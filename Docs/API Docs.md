# 5. API Documentation

## 5.1 Tổng Quan API

Face Attendance System cung cấp RESTful API được xây dựng trên FastAPI, hỗ trợ đầy đủ các chức năng quản lý người dùng và nhận diện khuôn mặt. API được thiết kế theo chuẩn REST với documentation tự động và validation mạnh mẽ.

### 5.1.1 Thông Tin Cơ Bản

```yaml
Base URL: http://localhost:8000
API Version: 1.0.0
Content-Type: application/json
Documentation: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

### 5.1.2 Đặc Điểm API

- **Auto-generated Documentation**: Swagger UI và ReDoc
- **Request Validation**: Pydantic models với type hints
- **Error Handling**: Standardized error responses
- **CORS Support**: Configurable cross-origin requests
- **Rate Limiting**: Configurable request limits (future)
- **Authentication**: JWT-based auth (future implementation)

## 5.2 Authentication và Security

### 5.2.1 Current Security Model

```python
# Hiện tại: No authentication required
# Future: JWT-based authentication

# Security Headers
{
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}

# Request Size Limits
MAX_REQUEST_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024    # 10MB per image
```

### 5.2.2 Future Authentication Flow

```python
# JWT Authentication (Future Implementation)
POST /auth/login
{
    "username": "admin",
    "password": "secure_password"
}

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}

# Protected Endpoints
Authorization: Bearer <access_token>
```

## 5.3 Health Check Endpoint

### 5.3.1 GET /health

Kiểm tra trạng thái hệ thống và các dịch vụ liên quan.

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T08:30:00.000Z",
    "version": "1.0.0",
    "services": {
        "mongodb": "healthy",
        "qdrant": "healthy", 
        "face_detection": "available",
        "image_processing": "available"
    },
    "system_info": {
        "cpu_usage": 25.5,
        "memory_usage": 68.2,
        "disk_usage": 45.1,
        "uptime_seconds": 86400
    }
}
```

**Status Codes:**
- `200 OK`: Hệ thống hoạt động bình thường
- `503 Service Unavailable`: Một hoặc nhiều dịch vụ không khả dụng

**Service Status Values:**
- `healthy`: Dịch vụ hoạt động bình thường
- `degraded`: Dịch vụ hoạt động nhưng có vấn đề
- `unhealthy`: Dịch vụ không khả dụng
- `unknown`: Không thể xác định trạng thái

## 5.4 User Management Endpoints

### 5.4.1 GET /users

Lấy danh sách tất cả người dùng với thông tin cơ bản và thumbnail.

**Request:**
```http
GET /users HTTP/1.1
Host: localhost:8000
```

**Query Parameters:**
```python
# Optional filtering (future implementation)
?department=Engineering          # Filter by department
&status=active                  # Filter by status
&limit=50                       # Limit results
&offset=0                       # Pagination offset
&search=john                    # Search by name/email
```

**Response:**
```json
[
    {
        "id": "507f1f77bcf86cd799439011",
        "name": "Nguyễn Văn An",
        "email": "nguyen.van.an@company.com",
        "phone": "+84901234567",
        "department": "Phòng Kỹ Thuật",
        "images": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "thumbnail": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002", 
                "thumbnail": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
            }
        ],
        "created_at": "2024-01-15T08:30:00.000Z",
        "updated_at": "2024-01-15T08:30:00.000Z",
        "status": "active",
        "metadata": {
            "total_images": 2,
            "last_recognition": "2024-01-20T09:15:00.000Z",
            "recognition_count": 45
        }
    }
]
```

**Status Codes:**
- `200 OK`: Thành công
- `500 Internal Server Error`: Lỗi server

### 5.4.2 POST /users

Tạo người dùng mới với thông tin cá nhân và ảnh khuôn mặt.

**Request:**
```http
POST /users HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "name": "Trần Thị Bình",
    "email": "tran.thi.binh@company.com",
    "phone": "+84987654321",
    "department": "Phòng Nhân Sự",
    "images": [
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAoACgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigAooooAKKKKACiiigD//2Q==",
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    ]
}
```

**Validation Rules:**
```python
class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(...)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    images: List[str] = Field(..., min_items=1, max_items=5)
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-ZÀ-ỹ\s]+$', v):
            raise ValueError('Name must contain only letters and spaces')
        return v.strip()
    
    @validator('images')
    def validate_images(cls, v):
        for img in v:
            # Validate base64 format
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', img):
                raise ValueError('Invalid base64 image format')
        return v
```

**Response:**
```json
{
    "id": "507f1f77bcf86cd799439012",
    "name": "Trần Thị Bình",
    "email": "tran.thi.binh@company.com",
    "phone": "+84987654321",
    "department": "Phòng Nhân Sự",
    "images": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "thumbnail": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "thumbnail": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
        }
    ],
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z",
    "status": "active",
    "metadata": {
        "total_images": 2,
        "last_recognition": null,
        "recognition_count": 0
    }
}
```

**Status Codes:**
- `201 Created`: Tạo thành công
- `400 Bad Request`: Dữ liệu không hợp lệ
- `409 Conflict`: Email đã tồn tại
- `413 Request Entity Too Large`: File quá lớn
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Lỗi server

### 5.4.3 PUT /users/{user_id}

Cập nhật thông tin người dùng (không bao gồm ảnh).

**Request:**
```http
PUT /users/507f1f77bcf86cd799439011 HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "name": "Nguyễn Văn An (Updated)",
    "phone": "+84901234568",
    "department": "Phòng Kỹ Thuật Senior"
}
```

**Path Parameters:**
- `user_id`: MongoDB ObjectId của người dùng

**Request Body:** (Tất cả fields đều optional)
```python
class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None  # Email không được thay đổi
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
```

**Response:** Giống như POST /users

**Status Codes:**
- `200 OK`: Cập nhật thành công
- `400 Bad Request`: Dữ liệu không hợp lệ
- `404 Not Found`: Không tìm thấy người dùng
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Lỗi server

### 5.4.4 DELETE /users/{user_id}

Xóa người dùng khỏi hệ thống (bao gồm tất cả ảnh và face vectors).

**Request:**
```http
DELETE /users/507f1f77bcf86cd799439011 HTTP/1.1
Host: localhost:8000
```

**Response:**
```http
HTTP/1.1 204 No Content
```

**Status Codes:**
- `204 No Content`: Xóa thành công
- `404 Not Found`: Không tìm thấy người dùng
- `500 Internal Server Error`: Lỗi server

### 5.4.5 POST /users/{user_id}/images

Thêm ảnh mới cho người dùng hiện có.

**Request:**
```http
POST /users/507f1f77bcf86cd799439011/images HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "images": [
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAoACgDASIAAhEBAxEB..."
    ]
}
```

**Validation:**
- Tổng số ảnh sau khi thêm không được vượt quá 5
- Mỗi ảnh phải là base64 hợp lệ
- Kích thước ảnh không vượt quá 10MB

**Response:** Thông tin người dùng đã cập nhật với ảnh mới

**Status Codes:**
- `200 OK`: Thêm ảnh thành công
- `400 Bad Request`: Vượt quá giới hạn ảnh hoặc format không hợp lệ
- `404 Not Found`: Không tìm thấy người dùng
- `413 Request Entity Too Large`: Ảnh quá lớn
- `500 Internal Server Error`: Lỗi server

## 5.5 Face Recognition Endpoint

### 5.5.1 POST /search

Tìm kiếm người dùng bằng nhận diện khuôn mặt.

**Request:**
```http
POST /search HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "image": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAoACgDASIAAhEBAxEB...",
    "options": {
        "threshold": 0.8,
        "max_results": 5,
        "include_confidence": true
    }
}
```

**Request Body:**
```python
class FaceSearchRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image")
    options: Optional[dict] = Field(default_factory=dict)
    
    @validator('image')
    def validate_image(cls, v):
        # Validate base64 format and decode to check if valid image
        try:
            image_data = base64.b64decode(v)
            Image.open(io.BytesIO(image_data))
        except Exception:
            raise ValueError('Invalid image data')
        return v
```

**Successful Match Response:**
```json
{
    "match_found": true,
    "user_info": {
        "id": "507f1f77bcf86cd799439011",
        "name": "Nguyễn Văn An",
        "email": "nguyen.van.an@company.com",
        "phone": "+84901234567",
        "department": "Phòng Kỹ Thuật",
        "images": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "thumbnail": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
            }
        ],
        "created_at": "2024-01-15T08:30:00.000Z",
        "updated_at": "2024-01-15T08:30:00.000Z"
    },
    "confidence": 0.95,
    "similarity_score": 0.95,
    "confidence_level": "very_high",
    "message": "Match found with 95.0% confidence",
    "processing_info": {
        "faces_detected": 1,
        "processing_time_ms": 245,
        "face_quality": {
            "brightness": 0.8,
            "contrast": 0.9,
            "sharpness": 0.85,
            "overall": 0.85
        }
    }
}
```

**No Match Response:**
```json
{
    "match_found": false,
    "user_info": null,
    "confidence": null,
    "similarity_score": null,
    "confidence_level": null,
    "message": "No matching user found",
    "processing_info": {
        "faces_detected": 1,
        "processing_time_ms": 180,
        "highest_similarity": 0.72,
        "face_quality": {
            "brightness": 0.6,
            "contrast": 0.7,
            "sharpness": 0.8,
            "overall": 0.7
        }
    }
}
```

**Multiple Faces Response:**
```json
{
    "match_found": true,
    "user_info": {
        "id": "507f1f77bcf86cd799439011",
        "name": "Nguyễn Văn An",
        // ... user info
    },
    "confidence": 0.92,
    "message": "Match found with 92.0% confidence",
    "processing_info": {
        "faces_detected": 3,
        "processing_time_ms": 420,
        "individual_faces": [
            {
                "face_index": 0,
                "bbox": {"x1": 120, "y1": 80, "x2": 220, "y2": 180},
                "confidence": 0.95,
                "match_found": true,
                "similarity_score": 0.92
            },
            {
                "face_index": 1,
                "bbox": {"x1": 300, "y1": 90, "x2": 400, "y2": 190},
                "confidence": 0.88,
                "match_found": false,
                "similarity_score": 0.65
            },
            {
                "face_index": 2,
                "bbox": {"x1": 450, "y1": 100, "x2": 550, "y2": 200},
                "confidence": 0.82,
                "match_found": false,
                "similarity_score": 0.58
            }
        ]
    }
}
```

**Status Codes:**
- `200 OK`: Xử lý thành công (có thể có hoặc không có match)
- `400 Bad Request`: Ảnh không hợp lệ hoặc không phát hiện được khuôn mặt
- `413 Request Entity Too Large`: Ảnh quá lớn
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Lỗi server
- `503 Service Unavailable`: AI services không khả dụng

## 5.6 Error Handling

### 5.6.1 Standardized Error Response

Tất cả lỗi đều trả về format chuẩn:

```json
{
    "error": "error_code",
    "message": "Human readable error message",
    "details": {
        "field": "specific_field_with_error",
        "code": "validation_error_code",
        "additional_info": "Extra context information"
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "request_id": "req_123456789"
}
```

### 5.6.2 Common Error Codes

```python
# Validation Errors (400)
INVALID_EMAIL_FORMAT = "invalid_email_format"
INVALID_IMAGE_FORMAT = "invalid_image_format"
IMAGE_TOO_LARGE = "image_too_large"
TOO_MANY_IMAGES = "too_many_images"
INVALID_USER_ID = "invalid_user_id"

# Business Logic Errors (409, 404)
USER_ALREADY_EXISTS = "user_already_exists"
USER_NOT_FOUND = "user_not_found"
IMAGE_LIMIT_EXCEEDED = "image_limit_exceeded"

# Processing Errors (422)
NO_FACE_DETECTED = "no_face_detected"
FACE_DETECTION_FAILED = "face_detection_failed"
FACE_ENCODING_FAILED = "face_encoding_failed"
POOR_IMAGE_QUALITY = "poor_image_quality"

# System Errors (500, 503)
DATABASE_CONNECTION_ERROR = "database_connection_error"
AI_SERVICE_UNAVAILABLE = "ai_service_unavailable"
INTERNAL_SERVER_ERROR = "internal_server_error"
```

### 5.6.3 Error Examples

**Validation Error (400):**
```json
{
    "error": "validation_error",
    "message": "Request validation failed",
    "details": {
        "field": "email",
        "code": "invalid_email_format",
        "value": "invalid-email",
        "expected": "Valid email address"
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "request_id": "req_123456789"
}
```

**Business Logic Error (409):**
```json
{
    "error": "user_already_exists",
    "message": "User with this email already exists",
    "details": {
        "email": "nguyen.van.an@company.com",
        "existing_user_id": "507f1f77bcf86cd799439011"
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "request_id": "req_123456790"
}
```

**Processing Error (422):**
```json
{
    "error": "no_face_detected",
    "message": "No faces detected in the provided image",
    "details": {
        "image_size": "1920x1080",
        "detection_confidence_threshold": 0.5,
        "suggestions": [
            "Ensure the image contains a clear, visible face",
            "Check lighting conditions",
            "Try a different angle or distance"
        ]
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "request_id": "req_123456791"
}
```

**System Error (503):**
```json
{
    "error": "ai_service_unavailable",
    "message": "Face recognition service is temporarily unavailable",
    "details": {
        "service": "face_detection",
        "status": "unhealthy",
        "retry_after_seconds": 30
    },
    "timestamp": "2024-01-15T10:30:00.000Z",
    "request_id": "req_123456792"
}
```

## 5.7 Request/Response Examples

### 5.7.1 Complete User Workflow

**1. Create User:**
```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lê Văn Cường",
    "email": "le.van.cuong@company.com",
    "department": "Phòng Marketing",
    "images": ["'$(base64 -w 0 face1.jpg)'", "'$(base64 -w 0 face2.jpg)'"]
  }'
```

**2. Search by Face:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "'$(base64 -w 0 search_image.jpg)'"
  }'
```

**3. Update User:**
```bash
curl -X PUT "http://localhost:8000/users/507f1f77bcf86cd799439011" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Phòng Marketing Senior"
  }'
```

**4. Add More Images:**
```bash
curl -X POST "http://localhost:8000/users/507f1f77bcf86cd799439011/images" \
  -H "Content-Type: application/json" \
  -d '{
    "images": ["'$(base64 -w 0 additional_face.jpg)'"]
  }'
```

### 5.7.2 JavaScript/Node.js Examples

```javascript
// Face Attendance API Client
class FaceAttendanceAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }
    
    async createUser(userData) {
        const response = await fetch(`${this.baseURL}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`API Error: ${error.message}`);
        }
        
        return await response.json();
    }
    
    async searchByFace(base64Image) {
        const response = await fetch(`${this.baseURL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: base64Image })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Search Error: ${error.message}`);
        }
        
        return await response.json();
    }
    
    async getAllUsers() {
        const response = await fetch(`${this.baseURL}/users`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`API Error: ${error.message}`);
        }
        
        return await response.json();
    }
    
    // Convert file to base64
    fileToBase64(file) {
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
}

// Usage example
const api = new FaceAttendanceAPI();

// Create user with file input
document.getElementById('createUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const imageFiles = formData.getAll('images');
    
    try {
        // Convert images to base64
        const base64Images = await Promise.all(
            imageFiles.map(file => api.fileToBase64(file))
        );
        
        const userData = {
            name: formData.get('name'),
            email: formData.get('email'),
            department: formData.get('department'),
            images: base64Images
        };
        
        const result = await api.createUser(userData);
        console.log('User created:', result);
        
    } catch (error) {
        console.error('Error creating user:', error.message);
    }
});

// Face search with camera
async function searchWithCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();
        
        // Capture frame after 2 seconds
        setTimeout(async () => {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            // Convert to base64
            const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
            
            // Search
            const result = await api.searchByFace(base64Image);
            console.log('Search result:', result);
            
            // Stop camera
            stream.getTracks().forEach(track => track.stop());
            
        }, 2000);
        
    } catch (error) {
        console.error('Camera error:', error);
    }
}
```

### 5.7.3 Python Client Example

```python
import requests
import base64
from typing import List, Dict, Optional

class FaceAttendanceClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def create_user(self, name: str, email: str, image_paths: List[str], 
                   phone: str = None, department: str = None) -> Dict:
        """Create a new user with face images"""
        
        # Convert images to base64
        images = []
        for image_path in image_paths:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                images.append(image_data)
        
        user_data = {
            "name": name,
            "email": email,
            "images": images
        }
        
        if phone:
            user_data["phone"] = phone
        if department:
            user_data["department"] = department
        
        response = self.session.post(f"{self.base_url}/users", json=user_data)
        response.raise_for_status()
        
        return response.json()
    
    def search_by_face(self, image_path: str) -> Dict:
        """Search for user by face image"""
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        search_data = {"image": image_data}
        
        response = self.session.post(f"{self.base_url}/search", json=search_data)
        response.raise_for_status()
        
        return response.json()
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        
        response = self.session.get(f"{self.base_url}/users")
        response.raise_for_status()
        
        return response.json()
    
    def update_user(self, user_id: str, **kwargs) -> Dict:
        """Update user information"""
        
        response = self.session.put(f"{self.base_url}/users/{user_id}", json=kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def delete_user(self, user_id: str) -> None:
        """Delete user"""
        
        response = self.session.delete(f"{self.base_url}/users/{user_id}")
        response.raise_for_status()
    
    def add_user_images(self, user_id: str, image_paths: List[str]) -> Dict:
        """Add images to existing user"""
        
        images = []
        for image_path in image_paths:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                images.append(image_data)
        
        image_data = {"images": images}
        
        response = self.session.post(
            f"{self.base_url}/users/{user_id}/images", 
            json=image_data
        )
        response.raise_for_status()
        
        return response.json()
    
    def health_check(self) -> Dict:
        """Check system health"""
        
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        
        return response.json()

# Usage example
if __name__ == "__main__":
    client = FaceAttendanceClient()
    
    try:
        # Health check
        health = client.health_check()
        print(f"System status: {health['status']}")
        
        # Create user
        user = client.create_user(
            name="Phạm Thị Dung",
            email="pham.thi.dung@company.com",
            department="Phòng Kế Toán",
            image_paths=["face1.jpg", "face2.jpg"]
        )
        print(f"Created user: {user['id']}")
        
        # Search by face
        result = client.search_by_face("search_image.jpg")
        if result['match_found']:
            print(f"Found user: {result['user_info']['name']} "
                  f"(confidence: {result['confidence']:.2f})")
        else:
            print("No match found")
            
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
```

## 5.8 Rate Limiting và Performance

### 5.8.1 Current Limits

```python
# Current implementation (no rate limiting)
# Future implementation:
RATE_LIMITS = {
    "search": "10 requests per minute",
    "user_creation": "5 requests per minute", 
    "user_updates": "20 requests per minute",
    "image_uploads": "3 requests per minute"
}

# Request size limits
MAX_REQUEST_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024    # 10MB per image
MAX_IMAGES_PER_REQUEST = 5
```

### 5.8.2 Performance Metrics

```python
# Typical response times
RESPONSE_TIMES = {
    "GET /users": "< 100ms",
    "POST /users": "< 2000ms (depends on image count)",
    "POST /search": "< 1000ms (single face)",
    "PUT /users/{id}": "< 200ms",
    "DELETE /users/{id}": "< 500ms"
}

# Throughput capacity
THROUGHPUT = {
    "concurrent_searches": 10,
    "searches_per_minute": 100,
    "user_creations_per_hour": 50
}
```

## 5.9 Kết Luận

API của Face Attendance System được thiết kế với các đặc điểm:

### 5.9.1 Điểm Mạnh
1. **RESTful Design**: Tuân thủ chuẩn REST API
2. **Auto Documentation**: Swagger UI và ReDoc tự động
3. **Strong Validation**: Pydantic models với type safety
4. **Error Handling**: Standardized error responses
5. **Performance**: Optimized cho real-time processing

### 5.9.2 Security Features
1. **Input Validation**: Comprehensive validation cho tất cả inputs
2. **Request Size Limits**: Bảo vệ khỏi DoS attacks
3. **Error Information**: Không leak sensitive information
4. **CORS Support**: Configurable cross-origin policies

### 5.9.3 Developer Experience
1. **Interactive Docs**: Test API trực tiếp từ browser
2. **Client Libraries**: Examples cho multiple languages
3. **Clear Error Messages**: Detailed error information
4. **Consistent Responses**: Standardized response format

API này cung cấp foundation mạnh mẽ cho việc tích hợp face recognition vào các ứng dụng khác nhau, từ web applications đến mobile apps và IoT devices.