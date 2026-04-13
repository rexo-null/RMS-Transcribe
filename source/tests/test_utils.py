"""Tests for utility functions."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import format_time, sanitize_filename


class TestFormatTime:
    """Test time formatting utility."""

    def test_format_time_seconds(self):
        """Test formatting seconds only."""
        assert format_time(45.5) == "00:00:45"

    def test_format_time_minutes(self):
        """Test formatting with minutes."""
        assert format_time(125.0) == "00:02:05"

    def test_format_time_hours(self):
        """Test formatting with hours."""
        assert format_time(3665.0) == "01:01:05"

    def test_format_time_zero(self):
        """Test formatting zero."""
        assert format_time(0.0) == "00:00:00"


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_sanitize_simple(self):
        """Test simple filename."""
        assert sanitize_filename("test.txt") == "test.txt"

    def test_sanitize_with_spaces(self):
        """Test filename with spaces."""
        assert sanitize_filename("test file.txt") == "test_file.txt"

    def test_sanitize_special_chars(self):
        """Test filename with special characters."""
        assert sanitize_filename("test<file>.txt") == "test_file_.txt"

    def test_sanitize_empty(self):
        """Test empty filename."""
        assert sanitize_filename("") == "_"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
