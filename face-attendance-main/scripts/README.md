# Face Attendance System Scripts

This folder contains utility scripts for working with the Face Attendance System.

## Scripts Overview

### 1. `add_training_data.py`
Uploads training images from the `data/train` folder to the Face Attendance System via API using base64 encoded images.

### 2. `test_attendance.py`
Tests face recognition accuracy using images from the `data/test` folder with base64 encoded images.

## Recent Updates

🔄 **Base64 Migration**: Both scripts have been updated to use base64 encoded images instead of file uploads, providing better integration and performance.

## Prerequisites

1. **Start the Face Attendance System API**:
   ```bash
   # Make sure you're in the project root directory
   python -m src.api --host 0.0.0.0 --port 8000
   ```

2. **Start the required services** (MongoDB and Qdrant):
   ```bash
   # In the infrastructure directory
   cd infrastructure
   docker-compose up -d
   ```

## Usage

### Adding Training Data

**Basic usage** (upload all people from data/train):
```bash
python scripts/add_training_data.py
```

**Advanced options**:
```bash
# Upload only first 10 people
python scripts/add_training_data.py --max-people 10

# Use custom data path
python scripts/add_training_data.py --data-path /path/to/your/train/data

# Use different API URL
python scripts/add_training_data.py --api-url http://192.168.1.100:8000

# Don't skip existing users (may create duplicates)
python scripts/add_training_data.py --no-skip-existing
```

**Example output**:
```
🚀 Face Attendance System - Training Data Uploader
==================================================
✓ API is healthy: healthy
🔍 Checking for existing users...
Found 0 existing users
📁 Processing training data from: data/train
📊 Found 195 people to process

[1/195] Processing: ca sĩ Akira Phan
  📸 Found 5 images
  ✓ Created user: Akira Phan (ID: 507f1f77bcf86cd799439011) with 5 images

[2/195] Processing: ca sĩ Anh Thơ
  📸 Found 3 images
  ✓ Created user: Anh Thơ (ID: 507f1f77bcf86cd799439012) with 3 images
...
```

### Testing Attendance

**Basic usage** (test all people from data/test):
```bash
python scripts/test_attendance.py
```

**Advanced options**:
```bash
# Test only first 5 people
python scripts/test_attendance.py --max-people 5

# Test maximum 2 images per person
python scripts/test_attendance.py --max-images 2

# Random sampling for quick tests
python scripts/test_attendance.py --max-people 10 --random-sample

# Save detailed results to file
python scripts/test_attendance.py --output-file test_results.json

# Use custom test data path
python scripts/test_attendance.py --test-path /path/to/your/test/data
```

**Example output**:
```
🧪 Face Attendance System - Attendance Tester
============================================================
✓ API is healthy: healthy
🔍 Fetching registered users...
Found 195 registered users
🧪 Running attendance tests from: data/test
📊 Testing 195 people

==================================================
[1/195] 
👤 Testing: Akira Phan
  📸 Testing with 4 images
    [1/4] Testing: image1.jpg
      ✅ Match: Akira Phan (confidence: 0.923)
      ✅ Correct identification!
    [2/4] Testing: image2.jpg
      ✅ Match: Akira Phan (confidence: 0.887)
      ✅ Correct identification!
  📊 Results: 2/4 matches (50.0%), 2 correct (100.0%)
...

============================================================
📊 ATTENDANCE TEST STATISTICS
============================================================
Total tests performed:      780
Successful matches:         623
Failed matches:             157
No face detected:           45
API errors:                 0
Match rate:                 79.9%
Identification accuracy:    94.2%
Overall accuracy:           75.3%
Average confidence:         0.856
Confidence range:           0.801 - 0.987
============================================================
```

## Script Features

### Training Data Uploader Features:
- ✅ **Base64 encoding**: Images are encoded as base64 for better API integration
- ✅ **JSON requests**: Uses JSON format instead of multipart form data
- ✅ Automatic name extraction from folder names
- ✅ Vietnamese character handling
- ✅ Duplicate detection (skips existing users)
- ✅ Image validation and processing
- ✅ Progress tracking and statistics
- ✅ Error handling and retry logic
- ✅ Respects 5-image limit per user

### Attendance Tester Features:
- ✅ **Base64 encoding**: Images are encoded as base64 for better API integration
- ✅ **JSON requests**: Uses JSON format instead of multipart form data
- ✅ Comprehensive accuracy testing
- ✅ Fuzzy name matching for identification
- ✅ Detailed statistics and analysis
- ✅ False positive detection
- ✅ Confidence score tracking
- ✅ JSON export of results
- ✅ Performance analysis by registration status

## Data Structure Expected

### Training Data (`data/train/`):
```
data/train/
├── ca sĩ Akira Phan/
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── diễn viên Angela Phương Trinh/
│   ├── photo1.png
│   └── ...
└── hoa hậu Lan Khuê/
    ├── pic1.jpeg
    └── ...
```

### Test Data (`data/test/`):
```
data/test/
├── ca sĩ Akira Phan/
│   ├── test1.jpg
│   ├── test2.jpg
│   └── ...
├── diễn viên Angela Phương Trinh/
│   ├── test_photo1.png
│   └── ...
└── hoa hậu Lan Khuê/
    ├── test_pic1.jpeg
    └── ...
```

## Troubleshooting

### Common Issues:

1. **API Connection Error**:
   - Make sure the API is running: `python -m src.api`
   - Check the API URL is correct
   - Verify firewall settings

2. **Database Connection Error**:
   - Start Docker services: `docker-compose up -d`
   - Check Docker containers are running: `docker ps`

3. **Image Processing Errors**:
   - Ensure images are valid formats (JPG, PNG, etc.)
   - Check image file sizes (max 10MB per image)
   - Verify image dimensions (min 100x100, max 5000x5000)

4. **Memory Issues**:
   - Reduce `--max-people` parameter
   - Process in smaller batches
   - Ensure sufficient system memory

### Performance Tips:

1. **For large datasets**:
   - Use `--max-people` to process in batches
   - Run during off-peak hours
   - Monitor system resources

2. **For quick testing**:
   - Use `--random-sample` flag
   - Limit with `--max-people` and `--max-images`
   - Test with a subset first

3. **For production use**:
   - Save results with `--output-file`
   - Monitor API logs for errors
   - Set up proper error handling

## Output Files

### Training Upload Results:
The script provides real-time progress and final statistics in the console.

### Test Results JSON:
When using `--output-file`, creates a detailed JSON with:
- Overall statistics
- Per-person results
- Individual image test results
- Confidence scores
- Error details

Example structure:
```json
{
  "statistics": {
    "total_tests": 780,
    "successful_matches": 623,
    "correct_identifications": 587,
    "average_confidence": 0.856
  },
  "test_results": [
    {
      "person": "Akira Phan",
      "registered": true,
      "total_images": 4,
      "successful_matches": 3,
      "correct_identifications": 3,
      "results": [...]
    }
  ],
  "timestamp": "2024-12-23 10:30:45"
}
```