"""Tests for model manager."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from model_manager import ModelManager


class TestModelManager:
    """Test ModelManager functionality."""

    def test_initialization(self, tmp_path):
        """Test manager initialization."""
        manager = ModelManager(str(tmp_path))
        assert manager.models_dir == tmp_path
        assert tmp_path.exists()

    def test_check_model_whisper_not_downloaded(self, tmp_path):
        """Test check when model not present."""
        manager = ModelManager(str(tmp_path))
        # Should return False when model not downloaded
        # Note: This requires mocking the actual download logic
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
