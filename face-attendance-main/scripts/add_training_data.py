#!/usr/bin/env python3
"""
Script to add training images to the face attendance system via API.
Reads images from data/train folder and creates users in the system.
"""

import os
import sys
import requests
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
import time
import argparse

# Add src to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from config import config

class TrainingDataUploader:
    """Handles uploading training data to the face attendance API."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the uploader.
        
        Args:
            api_base_url: Base URL of the face attendance API
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set reasonable timeouts
        self.session.timeout = 30
        
        # Statistics
        self.stats = {
            'total_people': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'total_images': 0,
            'skipped_people': 0
        }
    
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
    
    def get_existing_users(self) -> Dict[str, str]:
        """
        Get list of existing users to avoid duplicates.
        
        Returns:
            Dictionary mapping email to user_id
        """
        try:
            response = self.session.get(f"{self.api_base_url}/users")
            if response.status_code == 200:
                users = response.json()
                return {user['email']: user['id'] for user in users}
            else:
                print(f"Warning: Could not fetch existing users: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch existing users: {e}")
            return {}
    
    def extract_person_info(self, folder_name: str) -> Dict[str, str]:
        """
        Extract person information from folder name.
        
        Args:
            folder_name: Name of the person's folder
            
        Returns:
            Dictionary with person information
        """
        # Remove common prefixes and clean up the name
        name = folder_name
        
        # Remove prefixes like "ca sĩ", "diễn viên", "hoa hậu"
        prefixes = ["ca sĩ ", "diễn viên ", "hoa hậu "]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        
        # Clean up the name
        name = name.strip()
        
        # Generate email (simple approach)
        # Convert Vietnamese characters and create email
        email_name = self._vietnamese_to_ascii(name.lower())
        email_name = ''.join(c if c.isalnum() else '_' for c in email_name)
        email = f"{email_name}@example.com"
        
        # Determine department based on original folder name
        department = "Unknown"
        if folder_name.startswith("ca sĩ"):
            department = "Singer"
        elif folder_name.startswith("diễn viên"):
            department = "Actor"
        elif folder_name.startswith("hoa hậu"):
            department = "Beauty Queen"
        
        return {
            'name': name,
            'email': email,
            'department': department,
            'phone': None  # Not available from folder names
        }
    
    def _vietnamese_to_ascii(self, text: str) -> str:
        """
        Convert Vietnamese characters to ASCII equivalents.
        
        Args:
            text: Vietnamese text
            
        Returns:
            ASCII equivalent
        """
        # Simple Vietnamese to ASCII mapping
        vietnamese_map = {
            'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
            'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
            'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
            'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
            'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
            'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
            'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
            'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
            'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
            'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
            'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
            'đ': 'd',
            'À': 'A', 'Á': 'A', 'Ạ': 'A', 'Ả': 'A', 'Ã': 'A',
            'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ậ': 'A', 'Ẩ': 'A', 'Ẫ': 'A',
            'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ặ': 'A', 'Ẳ': 'A', 'Ẵ': 'A',
            'È': 'E', 'É': 'E', 'Ẹ': 'E', 'Ẻ': 'E', 'Ẽ': 'E',
            'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ệ': 'E', 'Ể': 'E', 'Ễ': 'E',
            'Ì': 'I', 'Í': 'I', 'Ị': 'I', 'Ỉ': 'I', 'Ĩ': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ọ': 'O', 'Ỏ': 'O', 'Õ': 'O',
            'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ộ': 'O', 'Ổ': 'O', 'Ỗ': 'O',
            'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ợ': 'O', 'Ở': 'O', 'Ỡ': 'O',
            'Ù': 'U', 'Ú': 'U', 'Ụ': 'U', 'Ủ': 'U', 'Ũ': 'U',
            'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ự': 'U', 'Ử': 'U', 'Ữ': 'U',
            'Ỳ': 'Y', 'Ý': 'Y', 'Ỵ': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y',
            'Đ': 'D'
        }
        
        result = ""
        for char in text:
            result += vietnamese_map.get(char, char)
        return result
    
    def get_image_files(self, person_folder: Path) -> List[Path]:
        """
        Get all image files from a person's folder.
        
        Args:
            person_folder: Path to person's folder
            
        Returns:
            List of image file paths (max 5 as per system limit)
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = []
        
        for file_path in person_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                image_files.append(file_path)
        
        # Sort for consistent ordering and limit to 5 images
        image_files.sort()
        return image_files[:5]  # System limit is 5 images per user
    
    def create_user(self, person_info: Dict[str, str], image_files: List[Path]) -> bool:
        """
        Create a user via the API using base64 encoded images.
        
        Args:
            person_info: Person information dictionary
            image_files: List of image file paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert images to base64
            base64_images = []
            for i, image_file in enumerate(image_files):
                try:
                    with open(image_file, 'rb') as f:
                        image_bytes = f.read()
                        # Encode to base64
                        base64_string = base64.b64encode(image_bytes).decode('utf-8')
                        base64_images.append(base64_string)
                except Exception as e:
                    print(f"  ✗ Could not read image {image_file}: {e}")
                    continue
            
            if not base64_images:
                print(f"  ✗ No valid images found for {person_info['name']}")
                return False
            
            # Prepare JSON data
            data = {
                'name': person_info['name'],
                'email': person_info['email'],
                'department': person_info['department'],
                'images': base64_images
            }
            
            if person_info['phone']:
                data['phone'] = person_info['phone']
            
            # Make API request with JSON
            response = self.session.post(
                f"{self.api_base_url}/users",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=60  # Longer timeout for image upload
            )
            
            if response.status_code == 201:
                user_data = response.json()
                print(f"  ✓ Created user: {person_info['name']} (ID: {user_data['id']}) with {len(base64_images)} images")
                self.stats['total_images'] += len(base64_images)
                return True
            else:
                error_info = ""
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_info = error_data.get('message', str(error_data))
                    else:
                        error_info = str(error_data)
                except:
                    error_info = response.text[:200]
                
                print(f"  ✗ Failed to create user {person_info['name']}: {response.status_code} - {error_info}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Network error creating user {person_info['name']}: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Unexpected error creating user {person_info['name']}: {e}")
            return False
    
    def upload_training_data(self, train_data_path: str, max_people: int = None, skip_existing: bool = True) -> None:
        """
        Upload all training data from the specified path.
        
        Args:
            train_data_path: Path to training data folder
            max_people: Maximum number of people to process (None for all)
            skip_existing: Whether to skip existing users
        """
        train_path = Path(train_data_path)
        
        if not train_path.exists():
            print(f"✗ Training data path does not exist: {train_data_path}")
            return
        
        if not train_path.is_dir():
            print(f"✗ Training data path is not a directory: {train_data_path}")
            return
        
        print(f"📁 Processing training data from: {train_path}")
        
        # Get existing users if skip_existing is True
        existing_users = {}
        if skip_existing:
            print("🔍 Checking for existing users...")
            existing_users = self.get_existing_users()
            print(f"Found {len(existing_users)} existing users")
        
        # Get all person folders
        person_folders = [f for f in train_path.iterdir() if f.is_dir()]
        person_folders.sort()  # Sort for consistent processing order
        
        if max_people:
            person_folders = person_folders[:max_people]
        
        self.stats['total_people'] = len(person_folders)
        print(f"📊 Found {len(person_folders)} people to process")
        
        # Process each person
        for i, person_folder in enumerate(person_folders, 1):
            person_name = person_folder.name
            print(f"\n[{i}/{len(person_folders)}] Processing: {person_name}")
            
            # Extract person information
            person_info = self.extract_person_info(person_name)
            
            # Check if user already exists
            if skip_existing and person_info['email'] in existing_users:
                print(f"  ⏭️  Skipping existing user: {person_info['name']}")
                self.stats['skipped_people'] += 1
                continue
            
            # Get image files
            image_files = self.get_image_files(person_folder)
            
            if not image_files:
                print(f"  ⚠️  No images found for {person_info['name']}")
                self.stats['failed_uploads'] += 1
                continue
            
            print(f"  📸 Found {len(image_files)} images")
            
            # Create user
            if self.create_user(person_info, image_files):
                self.stats['successful_uploads'] += 1
            else:
                self.stats['failed_uploads'] += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        # Print final statistics
        self.print_statistics()
    
    def print_statistics(self) -> None:
        """Print upload statistics."""
        print("\n" + "="*50)
        print("📊 UPLOAD STATISTICS")
        print("="*50)
        print(f"Total people found:     {self.stats['total_people']}")
        print(f"Successful uploads:     {self.stats['successful_uploads']}")
        print(f"Failed uploads:         {self.stats['failed_uploads']}")
        print(f"Skipped (existing):     {self.stats['skipped_people']}")
        print(f"Total images uploaded:  {self.stats['total_images']}")
        
        success_rate = 0
        if self.stats['total_people'] > 0:
            processed = self.stats['successful_uploads'] + self.stats['failed_uploads']
            success_rate = (self.stats['successful_uploads'] / processed * 100) if processed > 0 else 0
        
        print(f"Success rate:           {success_rate:.1f}%")
        print("="*50)


def main():
    """Main function to run the training data uploader."""
    parser = argparse.ArgumentParser(description="Upload training data to Face Attendance System")
    parser.add_argument(
        '--data-path', 
        type=str, 
        default='data/train',
        help='Path to training data folder (default: data/train)'
    )
    parser.add_argument(
        '--api-url', 
        type=str, 
        default='http://localhost:8001',
        help='API base URL (default: http://localhost:8001)'
    )
    parser.add_argument(
        '--max-people', 
        type=int, 
        default=None,
        help='Maximum number of people to process (default: all)'
    )
    parser.add_argument(
        '--no-skip-existing', 
        action='store_true',
        help='Do not skip existing users (may cause duplicates)'
    )
    
    args = parser.parse_args()
    
    print("🚀 Face Attendance System - Training Data Uploader")
    print("="*50)
    
    # Initialize uploader
    uploader = TrainingDataUploader(args.api_url)
    
    # Check API health
    if not uploader.check_api_health():
        print("\n❌ Cannot proceed - API is not available")
        print("Make sure the Face Attendance System API is running:")
        print("  python -m src.api --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Upload training data
    uploader.upload_training_data(
        train_data_path=args.data_path,
        max_people=args.max_people,
        skip_existing=not args.no_skip_existing
    )
    
    print("\n✅ Training data upload completed!")


if __name__ == "__main__":
    main()