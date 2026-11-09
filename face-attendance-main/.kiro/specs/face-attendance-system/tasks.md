# Implementation Plan: Face Attendance System

## Overview

Kế hoạch implementation cho hệ thống điểm danh khuôn mặt đơn giản và ngắn gọn nhất có thể. Sử dụng Python với Anaconda environment 'face', chạy trên CPU, với cấu trúc code tối giản. Database được deploy trong folder infrastructure, service chính được deploy bằng Docker Compose riêng biệt.

## Tasks

- [x] 1. Setup project structure and dependencies
  - Create minimal Python project structure with essential directories only
  - Setup requirements.txt with core dependencies (FastAPI, ultralytics, facenet-pytorch, pymongo, qdrant-client, Pillow, numpy)
  - Create simple configuration for Anaconda 'face' environment
  - Keep code structure as simple and minimal as possible
  - _Requirements: 5.4_

- [x] 1.1 Setup testing framework
  - Configure pytest and hypothesis for minimal testing setup
  - Create simple test structure for essential tests only
  - _Requirements: Testing Strategy_

- [x] 2. Implement core image processing components
  - [x] 2.1 Create ImageProcessor class
    - Implement image resizing to 600px width maintaining aspect ratio
    - Implement thumbnail generation (150x150px)
    - Implement base64 encoding/decoding functions
    - _Requirements: 6.2, 6.3, 6.5_

  - [x] 2.2 Write property tests for ImageProcessor
    - **Property 20: Image resizing consistency**
    - **Property 21: Thumbnail generation consistency**
    - **Property 23: Base64 storage format**
    - **Validates: Requirements 6.2, 6.3, 6.5**

  - [x] 2.3 Implement Face Detector using YOLOv8n
    - Load YOLOv8n model for face detection
    - Implement face detection with bounding box extraction
    - Implement face cropping with appropriate padding
    - _Requirements: 1.1, 6.1_

  - [x] 2.4 Write property tests for Face Detector
    - **Property 1: Face detection consistency**
    - **Property 19: Face cropping consistency**
    - **Validates: Requirements 1.1, 6.1**

- [x] 3. Implement face recognition components
  - [x] 3.1 Create Face Encoder using FaceNet
    - Load pre-trained FaceNet model
    - Implement face normalization preprocessing
    - Implement 512-dimensional vector encoding
    - _Requirements: 1.2, 6.4_

  - [ ]* 3.2 Write property tests for Face Encoder
    - **Property 2: Face encoding dimension consistency**
    - **Property 22: Face normalization**
    - **Validates: Requirements 1.2, 6.4**

  - [x] 3.3 Create FaceManager class
    - Integrate face detection and encoding
    - Implement similarity search with cosine distance
    - Implement threshold-based matching (0.8)
    - _Requirements: 1.3, 1.4_

  - [ ]* 3.4 Write property tests for FaceManager
    - **Property 3: Comprehensive face search**
    - **Property 4: Similarity threshold matching**
    - **Validates: Requirements 1.3, 1.4**

- [x] 4. Checkpoint - Ensure core face processing works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement database connections
  - [x] 5.1 Create MongoDB connection and User model
    - Setup MongoDB connection with pymongo
    - Define User document schema with multiple images support
    - Implement basic CRUD operations for users
    - _Requirements: 4.1_

  - [ ]* 5.2 Write property tests for MongoDB operations
    - **Property 16: MongoDB persistence**
    - **Validates: Requirements 4.1**

  - [x] 5.3 Create Qdrant connection and vector operations
    - Setup Qdrant client connection
    - Create collection for face vectors with proper configuration
    - Implement vector storage and search operations
    - _Requirements: 4.2_

  - [ ]* 5.4 Write property tests for Qdrant operations
    - **Property 17: Qdrant vector indexing**
    - **Validates: Requirements 4.2**

- [x] 6. Implement User Manager
  - [x] 6.1 Create UserManager class
    - Implement user creation with image limit validation (max 5)
    - Implement user retrieval with all thumbnails
    - Implement user update preserving face vectors
    - Implement complete user deletion (MongoDB + Qdrant)
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [ ]* 6.2 Write property tests for UserManager
    - **Property 5: User creation completeness**
    - **Property 6: Image limit enforcement**
    - **Property 7: Update preservation**
    - **Property 8: Complete deletion**
    - **Property 9: Complete user listing**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6**

  - [x] 6.3 Implement input validation and error handling
    - Add comprehensive input validation for user data
    - Implement proper error messages for validation failures
    - Handle edge cases like duplicate users and invalid formats
    - _Requirements: 2.7, 6.6_

  - [ ]* 6.4 Write property tests for validation
    - **Property 10: Input validation**
    - **Property 24: Unsupported format handling**
    - **Validates: Requirements 2.7, 6.6**

- [x] 7. Checkpoint - Ensure user management works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement FastAPI server
  - [x] 8.1 Create FastAPI application structure
    - Setup FastAPI app with proper middleware
    - Configure CORS and request/response models
    - Implement health check endpoint
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 8.2 Implement face search endpoint
    - Create POST /search endpoint accepting image upload
    - Integrate with FaceManager for face recognition
    - Return matching user information or no-match response
    - _Requirements: 3.1_

  - [ ]* 8.3 Write property tests for search endpoint
    - **Property 11: API search functionality**
    - **Validates: Requirements 3.1**

  - [x] 8.4 Implement user management endpoints
    - Create GET /users endpoint returning all users with thumbnails
    - Create POST /users endpoint for user creation with images
    - Create PUT /users/{id} endpoint for user updates
    - Create DELETE /users/{id} endpoint for user deletion
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [ ]* 8.5 Write property tests for user endpoints
    - **Property 12: API user listing**
    - **Property 13: API user creation**
    - **Property 14: API user update**
    - **Property 15: API user deletion**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

- [x] 9. Implement error handling and resilience
  - [x] 9.1 Add database error handling
    - Implement connection retry logic with exponential backoff
    - Handle database failures gracefully
    - Add proper logging for debugging
    - _Requirements: 4.5_

  - [ ]* 9.2 Write property tests for error handling
    - **Property 18: Database error handling**
    - **Validates: Requirements 4.5**

  - [x] 9.3 Add API error handling
    - Implement proper HTTP status codes and error responses
    - Handle file upload errors and size limits
    - Add request validation and sanitization
    - _Requirements: Error Handling section_

- [ ] 10. Create Docker infrastructure
  - [ ] 10.1 Create database Docker Compose in infrastructure folder
    - Create infrastructure/docker-compose.yml for MongoDB and Qdrant only
    - Configure persistent volumes in infrastructure/volumes/ directory
    - Keep configuration minimal and simple
    - _Requirements: 5.1, 5.3_

  - [ ] 10.2 Create application Dockerfile for Anaconda environment
    - Create simple Dockerfile that uses Anaconda 'face' environment
    - Configure for CPU-only execution (no GPU dependencies)
    - Keep Dockerfile minimal and straightforward
    - _Requirements: 5.2, 5.4_

  - [ ] 10.3 Create main Docker Compose for service deployment
    - Create docker-compose.yml in root directory for complete system
    - Link application container with database services from infrastructure
    - Configure to use Anaconda 'face' environment
    - Keep configuration as simple as possible
    - _Requirements: 5.5_

- [x] 11. Integration and final testing
  - [x] 11.1 Create integration tests
    - Test complete face recognition workflow
    - Test API endpoints with real database connections
    - Test error scenarios and edge cases
    - _Requirements: All requirements integration_

  - [ ]* 11.2 Write end-to-end property tests
    - Test complete system workflows with random data
    - Validate data consistency across all components
    - Test system resilience under various conditions

- [x] 12. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify Docker deployment works correctly
  - Test all API endpoints with sample data

## Notes

- Code được thiết kế đơn giản và ngắn gọn nhất có thể
- Sử dụng Anaconda environment 'face' để chạy service
- Database infrastructure được tách riêng trong folder infrastructure/
- Service chính được deploy bằng Docker Compose riêng biệt
- Hệ thống chạy hoàn toàn trên CPU, không cần GPU
- Mỗi task tập trung vào tính năng cốt lõi, tránh phức tạp không cần thiết
- Database containers sử dụng persistent volumes trong infrastructure/volumes/