#!/usr/bin/env python3
"""
Script to test attendance using images from data/test folder.
Tests face recognition by searching for faces in test images.
"""

import os
import sys
import requests
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import argparse
import random

# Add src to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from config import config

class AttendanceTester:
    """Handles testing attendance using the face attendance API."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the attendance tester.
        
        Args:
            api_base_url: Base URL of the face attendance API
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set reasonable timeouts
        self.session.timeout = 30
        
        # Statistics
        self.stats = {
            'total_tests': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'no_face_detected': 0,
            'api_errors': 0,
            'correct_identifications': 0,
            'incorrect_identifications': 0,
            'total_confidence': 0.0,
            'confidence_scores': []
        }
        
        # Store test results for detailed analysis
        self.test_results = []
    
    def check_api_health(self) -> bool:
        """
        Check if the API is running and healthy.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✓ API is healthy: {health_data.get('status', 'unknown')}")
                return True
            else:
                print(f"✗ API health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Cannot connect to API: {e}")
            return False
    
    def get_registered_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of registered users for comparison.
        
        Returns:
            Dictionary mapping user names to user info
        """
        try:
            response = self.session.get(f"{self.api_base_url}/users")
            if response.status_code == 200:
                users = response.json()
                # Create mapping by name for easier lookup
                user_map = {}
                for user in users:
                    user_map[user['name']] = user
                return user_map
            else:
                print(f"Warning: Could not fetch registered users: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch registered users: {e}")
            return {}
    
    def extract_expected_name(self, folder_name: str) -> str:
        """
        Extract expected person name from test folder name.
        
        Args:
            folder_name: Name of the test folder
            
        Returns:
            Expected person name
        """
        # Remove common prefixes and clean up the name
        name = folder_name
        
        # Remove prefixes like "ca sĩ", "diễn viên", "hoa hậu"
        prefixes = ["ca sĩ ", "diễn viên ", "hoa hậu "]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        
        return name.strip()
    
    def get_test_images(self, person_folder: Path, max_images: int = None) -> List[Path]:
        """
        Get test image files from a person's folder.
        
        Args:
            person_folder: Path to person's test folder
            max_images: Maximum number of images to test (None for all)
            
        Returns:
            List of test image file paths
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = []
        
        for file_path in person_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                image_files.append(file_path)
        
        # Sort for consistent ordering
        image_files.sort()
        
        if max_images:
            image_files = image_files[:max_images]
        
        return image_files
    
    def test_face_recognition(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        Test face recognition for a single image using base64 encoding.
        
        Args:
            image_path: Path to test image
            
        Returns:
            API response dictionary or None if error
        """
        try:
            # Read and encode image as base64
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            # Prepare JSON data
            data = {
                'image': base64_string
            }
            
            response = self.session.post(
                f"{self.api_base_url}/search",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"    ✗ API error {response.status_code}: {response.text[:100]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Network error: {e}")
            return None
        except Exception as e:
            print(f"    ✗ Unexpected error: {e}")
            return None
    
    def is_name_match(self, expected_name: str, found_name: str) -> bool:
        """
        Check if the found name matches the expected name.
        Uses fuzzy matching to handle slight variations.
        
        Args:
            expected_name: Expected person name
            found_name: Name returned by API
            
        Returns:
            True if names match, False otherwise
        """
        # Normalize names for comparison
        expected = expected_name.lower().strip()
        found = found_name.lower().strip()
        
        # Exact match
        if expected == found:
            return True
        
        # Check if one name contains the other (for partial matches)
        if expected in found or found in expected:
            return True
        
        # Check word-by-word match (for reordered names)
        expected_words = set(expected.split())
        found_words = set(found.split())
        
        # If most words match, consider it a match
        if len(expected_words) > 0 and len(found_words) > 0:
            common_words = expected_words.intersection(found_words)
            match_ratio = len(common_words) / max(len(expected_words), len(found_words))
            return match_ratio >= 0.7  # 70% word match threshold
        
        return False
    
    def test_person_attendance(self, person_folder: Path, expected_name: str, 
                             registered_users: Dict[str, Dict], max_images: int = None) -> Dict[str, Any]:
        """
        Test attendance for a specific person using their test images.
        
        Args:
            person_folder: Path to person's test folder
            expected_name: Expected person name
            registered_users: Dictionary of registered users
            max_images: Maximum number of images to test per person
            
        Returns:
            Dictionary with test results for this person
        """
        print(f"\n👤 Testing: {expected_name}")
        
        # Check if person is registered
        is_registered = any(self.is_name_match(expected_name, user_name) 
                           for user_name in registered_users.keys())
        
        if not is_registered:
            print(f"  ⚠️  Person not found in registered users")
        
        # Get test images
        test_images = self.get_test_images(person_folder, max_images)
        
        if not test_images:
            print(f"  ⚠️  No test images found")
            return {
                'person': expected_name,
                'registered': is_registered,
                'total_images': 0,
                'results': []
            }
        
        print(f"  📸 Testing with {len(test_images)} images")
        
        person_results = {
            'person': expected_name,
            'registered': is_registered,
            'total_images': len(test_images),
            'successful_matches': 0,
            'correct_identifications': 0,
            'results': []
        }
        
        # Test each image
        for i, image_path in enumerate(test_images, 1):
            print(f"    [{i}/{len(test_images)}] Testing: {image_path.name}")
            
            # Test face recognition
            api_result = self.test_face_recognition(image_path)
            
            if api_result is None:
                # API error
                self.stats['api_errors'] += 1
                person_results['results'].append({
                    'image': image_path.name,
                    'status': 'api_error',
                    'match_found': False,
                    'correct': False
                })
                continue
            
            # Process API result
            match_found = api_result.get('match_found', False)
            confidence = api_result.get('confidence')
            message = api_result.get('message', '')
            
            result = {
                'image': image_path.name,
                'match_found': match_found,
                'confidence': confidence,
                'message': message,
                'correct': False
            }
            
            if not match_found:
                if 'No face detected' in message:
                    print(f"      ⚠️  No face detected")
                    result['status'] = 'no_face'
                    self.stats['no_face_detected'] += 1
                else:
                    print(f"      ❌ No match found (confidence: {confidence})")
                    result['status'] = 'no_match'
                    self.stats['failed_matches'] += 1
            else:
                # Match found
                found_user = api_result.get('user_info', {})
                found_name = found_user.get('name', 'Unknown')
                
                print(f"      ✅ Match: {found_name} (confidence: {confidence:.3f})")
                
                result['status'] = 'match'
                result['found_name'] = found_name
                result['found_user_id'] = found_user.get('id')
                
                self.stats['successful_matches'] += 1
                person_results['successful_matches'] += 1
                
                # Check if identification is correct
                if is_registered and self.is_name_match(expected_name, found_name):
                    print(f"      ✅ Correct identification!")
                    result['correct'] = True
                    self.stats['correct_identifications'] += 1
                    person_results['correct_identifications'] += 1
                elif is_registered:
                    print(f"      ❌ Incorrect identification (expected: {expected_name})")
                    self.stats['incorrect_identifications'] += 1
                else:
                    # Person not registered, so any match is technically incorrect
                    print(f"      ❌ False positive (person not registered)")
                    self.stats['incorrect_identifications'] += 1
                
                # Track confidence scores
                if confidence is not None:
                    self.stats['total_confidence'] += confidence
                    self.stats['confidence_scores'].append(confidence)
            
            person_results['results'].append(result)
            self.stats['total_tests'] += 1
            
            # Small delay between tests
            time.sleep(0.2)
        
        # Print person summary
        if person_results['total_images'] > 0:
            match_rate = (person_results['successful_matches'] / person_results['total_images']) * 100
            if is_registered and person_results['successful_matches'] > 0:
                accuracy = (person_results['correct_identifications'] / person_results['successful_matches']) * 100
                print(f"  📊 Results: {person_results['successful_matches']}/{person_results['total_images']} matches ({match_rate:.1f}%), {person_results['correct_identifications']} correct ({accuracy:.1f}%)")
            else:
                print(f"  📊 Results: {person_results['successful_matches']}/{person_results['total_images']} matches ({match_rate:.1f}%)")
        
        return person_results
    
    def run_attendance_tests(self, test_data_path: str, max_people: int = None, 
                           max_images_per_person: int = None, random_sample: bool = False) -> None:
        """
        Run attendance tests on all people in the test data folder.
        
        Args:
            test_data_path: Path to test data folder
            max_people: Maximum number of people to test (None for all)
            max_images_per_person: Maximum images per person (None for all)
            random_sample: Whether to randomly sample people/images
        """
        test_path = Path(test_data_path)
        
        if not test_path.exists():
            print(f"✗ Test data path does not exist: {test_data_path}")
            return
        
        if not test_path.is_dir():
            print(f"✗ Test data path is not a directory: {test_data_path}")
            return
        
        print(f"🧪 Running attendance tests from: {test_path}")
        
        # Get registered users
        print("🔍 Fetching registered users...")
        registered_users = self.get_registered_users()
        print(f"Found {len(registered_users)} registered users")
        
        # Get all test folders
        test_folders = [f for f in test_path.iterdir() if f.is_dir()]
        
        if random_sample:
            random.shuffle(test_folders)
        else:
            test_folders.sort()  # Sort for consistent processing order
        
        if max_people:
            test_folders = test_folders[:max_people]
        
        print(f"📊 Testing {len(test_folders)} people")
        
        # Test each person
        for i, person_folder in enumerate(test_folders, 1):
            expected_name = self.extract_expected_name(person_folder.name)
            
            print(f"\n[{i}/{len(test_folders)}] " + "="*50)
            
            person_results = self.test_person_attendance(
                person_folder, 
                expected_name, 
                registered_users,
                max_images_per_person
            )
            
            self.test_results.append(person_results)
        
        # Print final statistics
        self.print_statistics()
        self.print_detailed_analysis()
    
    def print_statistics(self) -> None:
        """Print test statistics."""
        print("\n" + "="*60)
        print("📊 ATTENDANCE TEST STATISTICS")
        print("="*60)
        
        print(f"Total tests performed:      {self.stats['total_tests']}")
        print(f"Successful matches:         {self.stats['successful_matches']}")
        print(f"Failed matches:             {self.stats['failed_matches']}")
        print(f"No face detected:           {self.stats['no_face_detected']}")
        print(f"API errors:                 {self.stats['api_errors']}")
        
        # Match rate
        if self.stats['total_tests'] > 0:
            match_rate = (self.stats['successful_matches'] / self.stats['total_tests']) * 100
            print(f"Match rate:                 {match_rate:.1f}%")
        
        # Accuracy (correct identifications among matches)
        if self.stats['successful_matches'] > 0:
            accuracy = (self.stats['correct_identifications'] / self.stats['successful_matches']) * 100
            print(f"Identification accuracy:    {accuracy:.1f}%")
        
        # Overall accuracy (correct identifications among all tests)
        if self.stats['total_tests'] > 0:
            overall_accuracy = (self.stats['correct_identifications'] / self.stats['total_tests']) * 100
            print(f"Overall accuracy:           {overall_accuracy:.1f}%")
        
        # Confidence statistics
        if self.stats['confidence_scores']:
            avg_confidence = sum(self.stats['confidence_scores']) / len(self.stats['confidence_scores'])
            min_confidence = min(self.stats['confidence_scores'])
            max_confidence = max(self.stats['confidence_scores'])
            print(f"Average confidence:         {avg_confidence:.3f}")
            print(f"Confidence range:           {min_confidence:.3f} - {max_confidence:.3f}")
        
        print("="*60)
    
    def print_detailed_analysis(self) -> None:
        """Print detailed analysis of test results."""
        print("\n📈 DETAILED ANALYSIS")
        print("="*60)
        
        # Analyze by registration status
        registered_people = [r for r in self.test_results if r['registered']]
        unregistered_people = [r for r in self.test_results if not r['registered']]
        
        print(f"Registered people tested:   {len(registered_people)}")
        print(f"Unregistered people tested: {len(unregistered_people)}")
        
        # Performance on registered people
        if registered_people:
            total_registered_tests = sum(p['total_images'] for p in registered_people)
            total_registered_matches = sum(p['successful_matches'] for p in registered_people)
            total_correct = sum(p['correct_identifications'] for p in registered_people)
            
            if total_registered_tests > 0:
                reg_match_rate = (total_registered_matches / total_registered_tests) * 100
                print(f"Registered match rate:      {reg_match_rate:.1f}%")
            
            if total_registered_matches > 0:
                reg_accuracy = (total_correct / total_registered_matches) * 100
                print(f"Registered accuracy:        {reg_accuracy:.1f}%")
        
        # False positives (matches on unregistered people)
        if unregistered_people:
            total_unreg_tests = sum(p['total_images'] for p in unregistered_people)
            total_false_positives = sum(p['successful_matches'] for p in unregistered_people)
            
            if total_unreg_tests > 0:
                false_positive_rate = (total_false_positives / total_unreg_tests) * 100
                print(f"False positive rate:        {false_positive_rate:.1f}%")
        
        # Top performers (registered people with high accuracy)
        print(f"\n🏆 TOP PERFORMERS:")
        registered_with_tests = [p for p in registered_people if p['total_images'] > 0]
        registered_with_tests.sort(key=lambda x: (x['correct_identifications'] / x['total_images']), reverse=True)
        
        for i, person in enumerate(registered_with_tests[:5], 1):
            accuracy = (person['correct_identifications'] / person['total_images']) * 100
            print(f"  {i}. {person['person']}: {person['correct_identifications']}/{person['total_images']} ({accuracy:.1f}%)")
        
        # Problem cases (registered people with low accuracy)
        print(f"\n⚠️  PROBLEM CASES:")
        problem_cases = [p for p in registered_with_tests if p['total_images'] > 0 and (p['correct_identifications'] / p['total_images']) < 0.5]
        problem_cases.sort(key=lambda x: (x['correct_identifications'] / x['total_images']))
        
        for i, person in enumerate(problem_cases[:5], 1):
            accuracy = (person['correct_identifications'] / person['total_images']) * 100
            print(f"  {i}. {person['person']}: {person['correct_identifications']}/{person['total_images']} ({accuracy:.1f}%)")
        
        print("="*60)
    
    def save_results_to_file(self, output_file: str) -> None:
        """
        Save detailed test results to a JSON file.
        
        Args:
            output_file: Path to output file
        """
        results_data = {
            'statistics': self.stats,
            'test_results': self.test_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"\n❌ Failed to save results: {e}")


def main():
    """Main function to run the attendance tester."""
    parser = argparse.ArgumentParser(description="Test attendance using Face Attendance System")
    parser.add_argument(
        '--test-path', 
        type=str, 
        default='data/test',
        help='Path to test data folder (default: data/test)'
    )
    parser.add_argument(
        '--api-url', 
        type=str, 
        default='http://localhost:8000',
        help='API base URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--max-people', 
        type=int, 
        default=None,
        help='Maximum number of people to test (default: all)'
    )
    parser.add_argument(
        '--max-images', 
        type=int, 
        default=None,
        help='Maximum number of images per person (default: all)'
    )
    parser.add_argument(
        '--random-sample', 
        action='store_true',
        help='Randomly sample people and images'
    )
    parser.add_argument(
        '--output-file', 
        type=str, 
        default=None,
        help='Save detailed results to JSON file'
    )
    
    args = parser.parse_args()
    
    print("🧪 Face Attendance System - Attendance Tester")
    print("="*60)
    
    # Initialize tester
    tester = AttendanceTester(args.api_url)
    
    # Check API health
    if not tester.check_api_health():
        print("\n❌ Cannot proceed - API is not available")
        print("Make sure the Face Attendance System API is running:")
        print("  python -m src.api --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Run attendance tests
    tester.run_attendance_tests(
        test_data_path=args.test_path,
        max_people=args.max_people,
        max_images_per_person=args.max_images,
        random_sample=args.random_sample
    )
    
    # Save results if requested
    if args.output_file:
        tester.save_results_to_file(args.output_file)
    
    print("\n✅ Attendance testing completed!")


if __name__ == "__main__":
    main()