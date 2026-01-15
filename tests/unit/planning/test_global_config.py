"""Tests for global_config module."""

import json
from pathlib import Path

from aurora_planning.global_config import (
    DEFAULT_CONFIG,
    get_global_config,
    get_global_config_dir,
    get_global_data_dir,
    save_global_config,
)


class TestGetGlobalConfigDir:
    """Tests for get_global_config_dir function."""

    def test_returns_path(self):
        """Test returns a Path object."""
        result = get_global_config_dir()
        assert isinstance(result, Path)

    def test_contains_aurora(self):
        """Test path contains 'aurora'."""
        result = get_global_config_dir()
        assert "aurora" in str(result)

    def test_respects_xdg_config_home(self, monkeypatch, tmp_path):
        """Test respects XDG_CONFIG_HOME environment variable."""
        xdg_path = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))
        result = get_global_config_dir()
        assert result == xdg_path / "aurora"


class TestGetGlobalDataDir:
    """Tests for get_global_data_dir function."""

    def test_returns_path(self):
        """Test returns a Path object."""
        result = get_global_data_dir()
        assert isinstance(result, Path)

    def test_contains_aurora(self):
        """Test path contains 'aurora'."""
        result = get_global_data_dir()
        assert "aurora" in str(result)

    def test_respects_xdg_data_home(self, monkeypatch, tmp_path):
        """Test respects XDG_DATA_HOME environment variable."""
        xdg_path = tmp_path / "data"
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_path))
        result = get_global_data_dir()
        assert result == xdg_path / "aurora"


class TestGetGlobalConfig:
    """Tests for get_global_config function."""

    def test_returns_default_config_when_file_missing(self, monkeypatch, tmp_path):
        """Test returns default config when file doesn't exist."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config = get_global_config()
        assert "feature_flags" in config

    def test_creates_config_directory(self, monkeypatch, tmp_path):
        """Test creates config directory if it doesn't exist."""
        xdg_path = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))
        get_global_config()
        config_dir = xdg_path / "aurora"
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_reads_existing_config(self, monkeypatch, tmp_path):
        """Test reads existing configuration file."""
        xdg_path = tmp_path / "config"
        xdg_path.mkdir(parents=True)
        config_dir = xdg_path / "aurora"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        test_config = {"feature_flags": {"test_flag": True}}
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))
        config = get_global_config()
        assert config == test_config

    def test_returns_default_on_corrupt_config(self, monkeypatch, tmp_path):
        """Test returns default config when file is corrupt."""
        xdg_path = tmp_path / "config"
        xdg_path.mkdir(parents=True)
        config_dir = xdg_path / "aurora"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text("not valid json{{{")

        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))
        config = get_global_config()
        assert config == DEFAULT_CONFIG


class TestSaveGlobalConfig:
    """Tests for save_global_config function."""

    def test_saves_config_to_file(self, monkeypatch, tmp_path):
        """Test saves configuration to file."""
        xdg_path = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))

        test_config = {"feature_flags": {"new_feature": True}}
        save_global_config(test_config)

        config_file = xdg_path / "aurora" / "config.json"
        assert config_file.exists()

        saved_config = json.loads(config_file.read_text())
        assert saved_config == test_config

    def test_creates_directory_if_missing(self, monkeypatch, tmp_path):
        """Test creates config directory if it doesn't exist."""
        xdg_path = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_path))

        save_global_config(DEFAULT_CONFIG)

        config_dir = xdg_path / "aurora"
        assert config_dir.exists()
        assert config_dir.is_dir()
