#!/usr/bin/env python3
"""
Test script to verify Vietnamese name support in the Face Attendance System API.
"""

import base64
import requests
import json
from PIL import Image, ImageDraw
import io

def create_test_image_base64() -> str:
    """Create a test image and return as base64 string."""
    # Create a larger image to meet minimum size requirements
    img = Image.new('RGB', (300, 300), color='white')
    
    # Add detailed content to increase file size
    draw = ImageDraw.Draw(img)
    
    # Draw a face
    draw.ellipse([75, 75, 225, 225], outline='black', width=4)
    draw.ellipse([105, 120, 135, 150], fill='black')  # Left eye
    draw.ellipse([165, 120, 195, 150], fill='black')  # Right eye
    draw.arc([120, 180, 180, 210], start=0, end=180, fill='black', width=3)  # Mouth
    
    # Add texture to increase file size
    for i in range(0, 300, 10):
        for j in range(0, 300, 10):
            if (i + j) % 20 == 0:
                draw.rectangle([i, j, i+5, j+5], fill='lightgray')
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    
    encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return encoded_string

def test_vietnamese_names():
    """Test creating users with Vietnamese names."""
    base_url = "http://localhost:8001"
    
    # Test cases with Vietnamese names
    test_users = [
        {
            "name": "ca sĩ Bảo Thy",
            "email": "baothy@example.com",
            "phone": "0123456789",
            "department": "Entertainment"
        },
        {
            "name": "Nguyễn Văn An",
            "email": "nguyenvanan@example.com",
            "phone": "0987654321",
            "department": "Engineering"
        },
        {
            "name": "Trần Thị Hương Giang",
            "email": "tranhuonggiang@example.com",
            "department": "Marketing"
        },
        {
            "name": "Lê Minh Đức",
            "email": "leminhduc@example.com",
            "phone": "0555123456",
            "department": "Sales"
        }
    ]
    
    created_users = []
    
    print("Testing Vietnamese name support in Face Attendance System API")
    print("=" * 60)
    
    for i, user_info in enumerate(test_users, 1):
        print(f"\n{i}. Testing user: {user_info['name']}")
        
        # Create test image
        test_image_b64 = create_test_image_base64()
        
        # Prepare user data
        user_data = {
            **user_info,
            "images": [test_image_b64]
        }
        
        try:
            # Make API request
            response = requests.post(f"{base_url}/users", json=user_data)
            
            if response.status_code == 201:
                user = response.json()
                created_users.append(user['id'])
                print(f"   ✅ SUCCESS: User created with ID {user['id']}")
                print(f"      Name: {user['name']}")
                print(f"      Email: {user['email']}")
                print(f"      Images: {len(user['images'])} uploaded")
            else:
                print(f"   ❌ FAILED: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"      Error: {error_detail}")
                except:
                    print(f"      Error: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  CONNECTION ERROR: API server not running at {base_url}")
            print("      Please start the API server first")
            break
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
    
    # Clean up created users
    if created_users:
        print(f"\n🧹 Cleaning up {len(created_users)} created users...")
        for user_id in created_users:
            try:
                response = requests.delete(f"{base_url}/users/{user_id}")
                if response.status_code == 204:
                    print(f"   ✅ Deleted user {user_id}")
                else:
                    print(f"   ⚠️  Failed to delete user {user_id}: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error deleting user {user_id}: {e}")
    
    print("\n✅ Vietnamese name testing completed!")

if __name__ == "__main__":
    test_vietnamese_names()