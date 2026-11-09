"""
Pytest configuration and fixtures for face attendance system tests.
"""
import pytest
from hypothesis import settings

# Configure hypothesis for property-based testing
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")

@pytest.fixture
def sample_image_data():
    """Fixture providing sample image data for tests."""
    # This will be implemented when we have actual image processing
    return None

@pytest.fixture
def sample_user_data():
    """Fixture providing sample user data for tests."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "123456789",
        "department": "IT"
    }