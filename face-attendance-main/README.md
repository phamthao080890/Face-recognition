# Face Attendance System

A simple face recognition system for attendance tracking using Python, YOLO, and FaceNet.

## Project Structure

```
├── src/                    # Source code
│   ├── __init__.py
│   ├── api.py             # FastAPI server
│   ├── face_manager.py    # Face detection and recognition
│   ├── user_manager.py    # User management
│   └── image_processor.py # Image processing utilities
├── tests/                 # Test files
│   ├── __init__.py
│   ├── conftest.py        # Pytest configuration
│   └── test_*.py          # Test modules
├── infrastructure/        # Docker infrastructure
│   └── docker-compose.yml # MongoDB and Qdrant services
├── requirements.txt       # Python dependencies
├── environment.yml        # Anaconda environment
└── pytest.ini           # Pytest configuration
```

## Setup

### 1. Run Docker Infrastructure

Start the required services (MongoDB and Qdrant):

```bash
cd infrastructure
docker-compose up -d
```

This will start:
- **MongoDB** on port 27018 (user: admin, password: password123)
- **Qdrant** vector database on ports 6333/6334

To stop the services:
```bash
docker-compose down
```

### 2. Install Anaconda Environment

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate face
```

Alternative installation with pip:
```bash
pip install -r requirements.txt
```

### 3. Run API Server

Start the FastAPI server:

```bash
# From project root directory
python -m src.api

# Or with custom host/port
python -m src.api --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

## Development

This system uses:
- **FastAPI** for REST API
- **YOLOv8n** for face detection
- **FaceNet** for face encoding
- **MongoDB** for user data storage
- **Qdrant** for vector similarity search
- **Pytest + Hypothesis** for testing