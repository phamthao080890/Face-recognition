#!/usr/bin/env python3
"""
Test script for the updated base64 API endpoints.
"""

import base64
import requests
import json
from PIL import Image
import io

def image_to_base64(image_path):
    """Convert image file to base64 string"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def create_test_image():
    """Create a simple test image and return as base64"""
    # Create a larger image to meet minimum size requirements (>1KB)
    img = Image.new('RGB', (300, 300), color='white')
    
    # Add detailed content to increase file size
    from PIL import ImageDraw
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

def test_create_user():
    """Test creating a user with base64 images"""
    base_url = "http://localhost:8000"
    
    # Create test image
    test_image_b64 = create_test_image()
    
    # Prepare request data
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "123-456-7890",
        "department": "Engineering",
        "images": [test_image_b64]
    }
    
    # Make request
    response = requests.post(f"{base_url}/users", json=user_data)
    
    print(f"Create User Response Status: {response.status_code}")
    print(f"Create User Response: {response.json()}")
    
    return response.json() if response.status_code == 201 else None

def test_search_face():
    """Test face search with base64 image"""
    base_url = "http://localhost:8000"
    
    # Create test image
    test_image_b64 = create_test_image()
    
    # Prepare request data
    search_data = {
        "image": test_image_b64
    }
    
    # Make request
    response = requests.post(f"{base_url}/search", json=search_data)
    
    print(f"Search Face Response Status: {response.status_code}")
    print(f"Search Face Response: {response.json()}")

def test_add_images(user_id):
    """Test adding images to existing user"""
    base_url = "http://localhost:8000"
    
    # Create test image
    test_image_b64 = create_test_image()
    
    # Prepare request data
    images_data = {
        "images": [test_image_b64]
    }
    
    # Make request
    response = requests.post(f"{base_url}/users/{user_id}/images", json=images_data)
    
    print(f"Add Images Response Status: {response.status_code}")
    print(f"Add Images Response: {response.json()}")

if __name__ == "__main__":
    print("Testing Base64 API endpoints...")
    
    # Test create user
    print("\n1. Testing Create User...")
    user = test_create_user()
    
    if user:
        user_id = user.get('id')
        print(f"Created user with ID: {user_id}")
        
        # Test add images
        print("\n2. Testing Add Images...")
        test_add_images(user_id)
    
    # Test search face
    print("\n3. Testing Search Face...")
    test_search_face()
    
    print("\nTesting complete!")