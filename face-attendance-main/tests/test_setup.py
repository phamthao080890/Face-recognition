"""
Basic setup tests to verify the testing framework is working.
"""
import pytest
from hypothesis import given, strategies as st


def test_basic_setup():
    """Test that basic setup is working."""
    assert True


@given(st.integers())
def test_hypothesis_setup(x):
    """Test that hypothesis property-based testing is working."""
    # Feature: face-attendance-system, Property test: Basic hypothesis setup
    assert isinstance(x, int)