# Requirements Document

## Introduction

Hệ thống điểm danh khuôn mặt sử dụng Python với PyTorch và YOLO để nhận diện và quản lý thông tin người dùng thông qua khuôn mặt. Hệ thống sử dụng MongoDB để lưu trữ thông tin người dùng và Qdrant để lưu trữ vector khuôn mặt cho việc tìm kiếm nhanh chóng.

## Glossary

- **Face_Recognition_System**: Hệ thống chính xử lý nhận diện khuôn mặt
- **User_Manager**: Module quản lý thông tin người dùng
- **Face_Detector**: Module phát hiện khuôn mặt sử dụng YOLO
- **Face_Encoder**: Module mã hóa khuôn mặt thành vector sử dụng FaceNet
- **Vector_Store**: Qdrant database lưu trữ vector khuôn mặt
- **User_Database**: MongoDB lưu trữ thông tin người dùng
- **API_Server**: Server cung cấp REST API

## Requirements

### Requirement 1: Face Detection and Recognition

**User Story:** Là một người dùng, tôi muốn hệ thống có thể phát hiện và nhận diện khuôn mặt từ hình ảnh, để có thể thực hiện điểm danh tự động.

#### Acceptance Criteria

1. WHEN an image is provided, THE Face_Detector SHALL detect faces using YOLOv8n model
2. WHEN a face is detected, THE Face_Encoder SHALL generate a 512-dimensional vector using FaceNet
3. WHEN searching for a face, THE Vector_Store SHALL compare against all stored face vectors for each user
4. WHEN the highest similarity score is above 0.8, THE Face_Recognition_System SHALL consider it a match
5. WHEN no face is detected in an image, THE Face_Recognition_System SHALL return an appropriate error message

### Requirement 2: User Management

**User Story:** Là một quản trị viên, tôi muốn quản lý thông tin người dùng trong hệ thống, để có thể thêm, sửa, xóa và xem danh sách người dùng.

#### Acceptance Criteria

1. WHEN adding a new user, THE User_Manager SHALL store user information and face vectors in respective databases
2. WHEN adding images for a user, THE User_Manager SHALL allow maximum 5 images per user
3. WHEN a user already has 5 images and a new image is added, THE User_Manager SHALL reject the operation
4. WHEN updating user information, THE User_Manager SHALL modify existing records while preserving face vectors
5. WHEN deleting a user, THE User_Manager SHALL remove both user information and all associated face vectors
6. WHEN retrieving user list, THE User_Manager SHALL return user information with all thumbnail images
7. WHEN user information is invalid, THE User_Manager SHALL reject the operation and return validation errors

### Requirement 3: API Endpoints

**User Story:** Là một developer, tôi muốn có các API endpoints để tương tác với hệ thống, để có thể tích hợp vào các ứng dụng khác.

#### Acceptance Criteria

1. WHEN calling POST /search endpoint with an image, THE API_Server SHALL return matching user information
2. WHEN calling GET /users endpoint, THE API_Server SHALL return list of all users with thumbnails
3. WHEN calling POST /users endpoint with user data and image, THE API_Server SHALL create a new user
4. WHEN calling PUT /users/{id} endpoint, THE API_Server SHALL update existing user information
5. WHEN calling DELETE /users/{id} endpoint, THE API_Server SHALL remove the user from system

### Requirement 4: Database Integration

**User Story:** Là một system architect, tôi muốn hệ thống sử dụng MongoDB và Qdrant để lưu trữ dữ liệu hiệu quả, để đảm bảo hiệu suất và khả năng mở rộng.

#### Acceptance Criteria

1. WHEN storing user information, THE User_Database SHALL persist data in MongoDB collections with support for multiple images per user
2. WHEN storing face vectors, THE Vector_Store SHALL index multiple vectors per user in Qdrant for comprehensive face matching
3. WHEN querying face vectors, THE Vector_Store SHALL return results within 100ms for datasets under 10,000 faces
4. WHEN the system starts, THE Face_Recognition_System SHALL establish connections to both databases
5. WHEN database operations fail, THE Face_Recognition_System SHALL handle errors gracefully and retry connections

### Requirement 5: Deployment and Infrastructure

**User Story:** Là một DevOps engineer, tôi muốn hệ thống có thể deploy dễ dàng bằng Docker, để đảm bảo tính nhất quán giữa các môi trường.

#### Acceptance Criteria

1. WHEN deploying databases, THE infrastructure SHALL use Docker Compose to run MongoDB and Qdrant
2. WHEN deploying the application, THE API_Server SHALL run in a separate Docker container
3. WHEN starting the system, THE infrastructure SHALL mount persistent volumes for database data
4. WHEN the application starts, THE Face_Recognition_System SHALL run on CPU without GPU requirements
5. WHEN accessing the API, THE API_Server SHALL be available on a configurable port

### Requirement 6: Image Processing

**User Story:** Là một người dùng, tôi muốn hệ thống xử lý hình ảnh một cách chính xác, để đảm bảo chất lượng nhận diện khuôn mặt.

#### Acceptance Criteria

1. WHEN processing an image, THE Face_Detector SHALL crop detected faces with appropriate padding
2. WHEN storing user images, THE User_Manager SHALL resize images to 600 pixels width while maintaining aspect ratio
3. WHEN generating thumbnails, THE User_Manager SHALL create 150x150 pixel thumbnails for display
4. WHEN encoding faces, THE Face_Encoder SHALL normalize face images before processing
5. WHEN storing images, THE User_Database SHALL save both full images and thumbnails in base64 format
6. WHEN image format is unsupported, THE Face_Recognition_System SHALL return format error