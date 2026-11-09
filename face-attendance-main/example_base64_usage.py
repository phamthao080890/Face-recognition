#!/usr/bin/env python3
"""
Example usage of the Face Attendance System API with base64 encoded images.
"""

import base64
import requests
import json
from PIL import Image
import io

# API base URL
BASE_URL = "http://localhost:8000"

def image_file_to_base64(image_path: str) -> str:
    """Convert an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def create_sample_image_base64() -> str:
    """Create a sample image and return as base64 string."""
    # Create a larger image to meet minimum size requirements
    img = Image.new('RGB', (300, 300), color='white')
    
    # Draw a detailed face to make the image larger
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Face outline
    draw.ellipse([75, 75, 225, 225], outline='black', width=4)
    
    # Eyes
    draw.ellipse([105, 120, 135, 150], fill='black')
    draw.ellipse([165, 120, 195, 150], fill='black')
    
    # Eye highlights
    draw.ellipse([115, 125, 125, 135], fill='white')
    draw.ellipse([175, 125, 185, 135], fill='white')
    
    # Nose
    draw.polygon([(150, 160), (140, 180), (160, 180)], outline='black', width=2)
    
    # Mouth
    draw.arc([120, 190, 180, 220], start=0, end=180, fill='black', width=3)
    
    # Add some texture to increase file size
    for i in range(0, 300, 20):
        for j in range(0, 300, 20):
            if (i + j) % 40 == 0:
                draw.point((i, j), fill='lightgray')
    
    # Convert to bytes then base64
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)  # Higher quality for larger size
    buffer.seek(0)
    
    encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return encoded_string

def create_user_example():
    """Example: Create a new user with base64 images."""
    print("Creating a new user with base64 images...")
    
    # Create sample images
    image1_b64 = create_sample_image_base64()
    image2_b64 = create_sample_image_base64()  # You could create different images
    
    # Prepare user data
    user_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "department": "Engineering",
        "images": [image1_b64, image2_b64]
    }
    
    # Make API request
    response = requests.post(f"{BASE_URL}/users", json=user_data)
    
    if response.status_code == 201:
        user = response.json()
        print(f"✅ User created successfully!")
        print(f"   User ID: {user['id']}")
        print(f"   Name: {user['name']}")
        print(f"   Email: {user['email']}")
        print(f"   Images: {len(user['images'])} images uploaded")
        return user
    else:
        print(f"❌ Failed to create user: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def search_face_example():
    """Example: Search for a face using base64 image."""
    print("\nSearching for a face...")
    
    # Create search image
    search_image_b64 = create_sample_image_base64()
    
    # Prepare search data
    search_data = {
        "image": search_image_b64
    }
    
    # Make API request
    response = requests.post(f"{BASE_URL}/search", json=search_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Face search completed!")
        print(f"   Match found: {result['match_found']}")
        if result['match_found']:
            print(f"   Confidence: {result['confidence']}")
            print(f"   User: {result['user_info']['name']}")
        print(f"   Message: {result['message']}")
        return result
    else:
        print(f"❌ Face search failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def add_images_example(user_id: str):
    """Example: Add additional images to an existing user."""
    print(f"\nAdding images to user {user_id}...")
    
    # Create additional images
    new_image_b64 = create_sample_image_base64()
    
    # Prepare images data
    images_data = {
        "images": [new_image_b64]
    }
    
    # Make API request
    response = requests.post(f"{BASE_URL}/users/{user_id}/images", json=images_data)
    
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Images added successfully!")
        print(f"   Total images: {len(user['images'])}")
        return user
    else:
        print(f"❌ Failed to add images: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def update_user_example(user_id: str):
    """Example: Update user information."""
    print(f"\nUpdating user {user_id}...")
    
    # Prepare update data
    update_data = {
        "name": "John Smith",  # Updated name
        "phone": "+1-555-9876",  # Updated phone
        "department": "Senior Engineering"  # Updated department
    }
    
    # Make API request
    response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_data)
    
    if response.status_code == 200:
        user = response.json()
        print(f"✅ User updated successfully!")
        print(f"   Name: {user['name']}")
        print(f"   Phone: {user['phone']}")
        print(f"   Department: {user['department']}")
        return user
    else:
        print(f"❌ Failed to update user: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def get_all_users_example():
    """Example: Get all users."""
    print("\nRetrieving all users...")
    
    # Make API request
    response = requests.get(f"{BASE_URL}/users")
    
    if response.status_code == 200:
        users = response.json()
        print(f"✅ Retrieved {len(users)} users:")
        for user in users:
            print(f"   - {user['name']} ({user['email']}) - {len(user['images'])} images")
        return users
    else:
        print(f"❌ Failed to retrieve users: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def delete_user_example(user_id: str):
    """Example: Delete a user."""
    print(f"\nDeleting user {user_id}...")
    
    # Make API request
    response = requests.delete(f"{BASE_URL}/users/{user_id}")
    
    if response.status_code == 204:
        print(f"✅ User deleted successfully!")
        return True
    else:
        print(f"❌ Failed to delete user: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def health_check_example():
    """Example: Check API health."""
    print("Checking API health...")
    
    # Make API request
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        health = response.json()
        print(f"✅ API is {health['status']}")
        print(f"   Services: {health['services']}")
        return health
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return None

def main():
    """Run all examples."""
    print("Face Attendance System API - Base64 Examples")
    print("=" * 50)
    
    # Check API health first
    health = health_check_example()
    if not health or health['status'] != 'healthy':
        print("⚠️  API is not healthy. Please check your server.")
        return
    
    # Create a user
    user = create_user_example()
    if not user:
        return
    
    user_id = user['id']
    
    try:
        # Add more images
        add_images_example(user_id)
        
        # Update user info
        update_user_example(user_id)
        
        # Search for face
        search_face_example()
        
        # Get all users
        get_all_users_example()
        
    finally:
        # Clean up - delete the user
        delete_user_example(user_id)
    
    print("\n✅ All examples completed!")

if __name__ == "__main__":
    main()