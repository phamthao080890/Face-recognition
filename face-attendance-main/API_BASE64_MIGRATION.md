# Face Attendance System API - Base64 Migration Guide

## Overview

The Face Attendance System API has been updated to accept base64 encoded images instead of file uploads. This change provides better integration with web applications and mobile clients. The API also supports international names including Vietnamese, Chinese, Japanese, Arabic, Cyrillic, and other Unicode characters.

## What Changed

### Before (File Upload)
```bash
# Old API - Multipart form data
curl -X POST "http://localhost:8000/users" \
  -F "name=John Doe" \
  -F "email=john@example.com" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"
```

### After (Base64 JSON)
```bash
# New API - JSON with base64 images
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nguyễn Văn An",
    "email": "nguyenvanan@example.com",
    "images": ["base64_encoded_image_1", "base64_encoded_image_2"]
  }'
```

## Updated Endpoints

### 1. Create User - `POST /users`

**Request Body:**
```json
{
  "name": "ca sĩ Bảo Thy",
  "email": "baothy@example.com",
  "phone": "+84-123-456-789",
  "department": "Entertainment",
  "images": [
    "base64_encoded_image_1",
    "base64_encoded_image_2"
  ]
}
```

**International Name Support:**
The API supports names with international characters including:
- Vietnamese: `Nguyễn Văn An`, `ca sĩ Bảo Thy`
- Chinese: `李小明`, `王美丽`
- Japanese: `田中太郎`, `佐藤花子`
- Korean: `김철수`, `박영희`
- Arabic: `محمد علي`, `فاطمة أحمد`
- Russian: `Владимир Петров`, `Анна Иванова`
- Spanish: `José María`, `María José`
- French: `François Müller`, `Amélie Dubois`
- German: `Müller`, `Björn Andersson`

**Name Validation Rules:**
- Minimum 2 characters, maximum 100 characters
- Allowed characters: Letters (including accented/Unicode), numbers, spaces, hyphens (-), apostrophes (')
- Not allowed: Special symbols like @, #, $, %, etc.

### 2. Add User Images - `POST /users/{user_id}/images`

**Request Body:**
```json
{
  "images": [
    "base64_encoded_image_1",
    "base64_encoded_image_2"
  ]
}
```

### 3. Search Face - `POST /search`

**Request Body:**
```json
{
  "image": "base64_encoded_search_image"
}
```

### 4. Update User - `PUT /users/{user_id}`

**Request Body:**
```json
{
  "name": "Updated Name",
  "email": "updated@example.com",
  "phone": "+1-555-9999",
  "department": "Updated Department"
}
```

## Base64 Image Format

### Supported Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)

### Size Limits
- **Minimum:** 1KB per image
- **Maximum:** 10MB per image
- **Dimensions:** 32x32 to 4096x4096 pixels
- **Count:** 1-5 images per user

### Base64 Encoding

You can encode images with or without the data URL prefix:

```javascript
// With data URL prefix (optional)
"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."

// Without prefix (recommended)
"/9j/4AAQSkZJRgABAQEAYABgAAD..."
```

## Code Examples

### Python Example
```python
import base64
import requests

# Convert image file to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Create user with base64 images and Vietnamese name
image_b64 = image_to_base64("photo.jpg")
user_data = {
    "name": "Nguyễn Thị Lan Anh",
    "email": "lananh@example.com",
    "phone": "+84-987-654-321",
    "department": "Kỹ thuật",
    "images": [image_b64]
}

response = requests.post("http://localhost:8000/users", json=user_data)
```

### JavaScript Example
```javascript
// Convert file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // Remove data URL prefix
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
}

// Create user with base64 images
const imageFile = document.getElementById('imageInput').files[0];
const imageBase64 = await fileToBase64(imageFile);

const userData = {
    name: "Trần Minh Hoàng",
    email: "minhhoang@example.com",
    phone: "+84-123-456-789",
    department: "Phát triển phần mềm",
    images: [imageBase64]
};

const response = await fetch("http://localhost:8000/users", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify(userData)
});
```

## Migration Steps

1. **Update Client Code:** Change from multipart form data to JSON requests
2. **Convert Images:** Encode images as base64 strings before sending
3. **Update Headers:** Use `Content-Type: application/json` instead of `multipart/form-data`
4. **Test Endpoints:** Verify all endpoints work with the new format

## Benefits

- **Better Web Integration:** Easier to use with JavaScript/React/Vue applications
- **Mobile Friendly:** Simpler integration with mobile apps
- **JSON Consistency:** All API endpoints now use JSON format
- **No File Handling:** No need to manage temporary files on client side
- **International Support:** Full Unicode support for names in any language
- **Vietnamese Support:** Native support for Vietnamese names with diacritics

## Error Handling

The API provides detailed error messages for invalid base64 data:

```json
{
  "error": "validation_error",
  "message": "Name can only contain letters (including accented characters), numbers, spaces, hyphens, and apostrophes",
  "field": "name"
}
```

Common validation errors:
- `invalid_base64`: Malformed base64 string
- `image_too_large`: Image exceeds size limits
- `image_too_small`: Image below minimum size
- `unsupported_format`: Image format not supported
- `invalid_image`: Corrupted or invalid image data
- `validation_error`: Name contains invalid characters (only letters, numbers, spaces, hyphens, apostrophes allowed)

## Testing

Use the provided example scripts:
- `example_base64_usage.py` - Complete API usage examples
- `test_base64_api.py` - Simple test script
- `test_vietnamese_names.py` - Vietnamese name validation testing

## Backward Compatibility

⚠️ **Breaking Change:** The old file upload endpoints are no longer supported. All clients must be updated to use the new base64 format.

## Support

For questions or issues with the migration, please check:
1. Image encoding is correct base64 format
2. Image meets size and format requirements
3. Content-Type header is set to `application/json`
4. Request body is valid JSON