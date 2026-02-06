"""Unit tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest

from core.config import (
    Config,
    ModelConfig,
    IndexConfig,
    WatchConfig,
    OutputConfig,
    ProjectConfig,
    get_config,
)


@pytest.mark.unit
class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_values(self):
        """Test ModelConfig has correct defaults."""
        config = ModelConfig()
        assert config.name == "google/embeddinggemma-300m"
        assert config.device == "auto"
        assert config.batch_size == 32

    def test_custom_values(self):
        """Test ModelConfig with custom values."""
        config = ModelConfig(
            name="custom/model",
            device="cuda",
            batch_size=64
        )
        assert config.name == "custom/model"
        assert config.device == "cuda"
        assert config.batch_size == 64


@pytest.mark.unit
class TestIndexConfig:
    """Tests for IndexConfig dataclass."""

    def test_default_excluded_dirs(self):
        """Test IndexConfig has sensible default exclusions."""
        config = IndexConfig()
        assert "node_modules" in config.excluded_dirs
        assert ".venv" in config.excluded_dirs
        assert "__pycache__" in config.excluded_dirs
        assert ".git" in config.excluded_dirs

    def test_default_excluded_extensions(self):
        """Test IndexConfig has correct default excluded extensions."""
        config = IndexConfig()
        assert ".min.js" in config.excluded_extensions
        assert ".map" in config.excluded_extensions
        assert ".pyc" in config.excluded_extensions

    def test_default_max_file_size(self):
        """Test default max file size is 1MB."""
        config = IndexConfig()
        assert config.max_file_size_kb == 1024

    def test_custom_excluded_dirs(self):
        """Test IndexConfig with custom exclusions."""
        config = IndexConfig(excluded_dirs=["custom_dir"])
        assert config.excluded_dirs == ["custom_dir"]


@pytest.mark.unit
class TestWatchConfig:
    """Tests for WatchConfig dataclass."""

    def test_default_values(self):
        """Test WatchConfig has correct defaults."""
        config = WatchConfig()
        assert config.debounce_ms == 2000
        assert config.auto_start is False

    def test_custom_values(self):
        """Test WatchConfig with custom values."""
        config = WatchConfig(debounce_ms=5000, auto_start=True)
        assert config.debounce_ms == 5000
        assert config.auto_start is True


@pytest.mark.unit
class TestOutputConfig:
    """Tests for OutputConfig dataclass."""

    def test_default_values(self):
        """Test OutputConfig has correct defaults."""
        config = OutputConfig()
        assert config.context_lines == 0
        assert config.show_score is False
        assert config.truncate_lines == 120
        assert config.color == "auto"

    def test_custom_values(self):
        """Test OutputConfig with custom values."""
        config = OutputConfig(
            context_lines=3,
            show_score=True,
            truncate_lines=80,
            color="always"
        )
        assert config.context_lines == 3
        assert config.show_score is True
        assert config.truncate_lines == 80
        assert config.color == "always"


@pytest.mark.unit
class TestProjectConfig:
    """Tests for ProjectConfig dataclass."""

    def test_from_path_creates_unique_hash(self):
        """Test that different paths create different hashes."""
        base_storage = Path("/tmp/storage")

        config1 = ProjectConfig.from_path(Path("/project/a"), base_storage)
        config2 = ProjectConfig.from_path(Path("/project/b"), base_storage)

        assert config1.project_hash != config2.project_hash

    def test_from_path_same_path_same_hash(self):
        """Test that same path creates same hash."""
        base_storage = Path("/tmp/storage")

        config1 = ProjectConfig.from_path(Path("/project/a"), base_storage)
        config2 = ProjectConfig.from_path(Path("/project/a"), base_storage)

        assert config1.project_hash == config2.project_hash

    def test_from_path_project_name(self):
        """Test project name is derived from path."""
        base_storage = Path("/tmp/storage")
        config = ProjectConfig.from_path(Path("/home/user/my-project"), base_storage)

        assert config.project_name == "my-project"

    def test_from_path_storage_dir(self):
        """Test storage directory structure."""
        base_storage = Path("/tmp/storage")
        config = ProjectConfig.from_path(Path("/home/user/project"), base_storage)

        assert config.storage_dir.parent == base_storage / "projects"
        assert config.project_name in str(config.storage_dir)

    def test_index_dir_property(self):
        """Test index_dir property."""
        config = ProjectConfig(
            project_path=Path("/project"),
            project_name="project",
            project_hash="abc123",
            storage_dir=Path("/storage/project_abc123")
        )
        assert config.index_dir == Path("/storage/project_abc123/index")

    def test_snapshot_dir_property(self):
        """Test snapshot_dir property."""
        config = ProjectConfig(
            project_path=Path("/project"),
            project_name="project",
            project_hash="abc123",
            storage_dir=Path("/storage/project_abc123")
        )
        assert config.snapshot_dir == Path("/storage/project_abc123/snapshots")

    def test_project_info_file_property(self):
        """Test project_info_file property."""
        config = ProjectConfig(
            project_path=Path("/project"),
            project_name="project",
            project_hash="abc123",
            storage_dir=Path("/storage/project_abc123")
        )
        assert config.project_info_file == Path("/storage/project_abc123/project_info.json")

    def test_watcher_pid_file_property(self):
        """Test watcher_pid_file property."""
        config = ProjectConfig(
            project_path=Path("/project"),
            project_name="project",
            project_hash="abc123",
            storage_dir=Path("/storage/project_abc123")
        )
        assert config.watcher_pid_file == Path("/storage/project_abc123/watcher.pid")

    def test_lock_file_property(self):
        """Test lock_file property."""
        config = ProjectConfig(
            project_path=Path("/project"),
            project_name="project",
            project_hash="abc123",
            storage_dir=Path("/storage/project_abc123")
        )
        assert config.lock_file == Path("/storage/project_abc123/index.lock")

    def test_is_indexed_false_when_no_index(self):
        """Test is_indexed returns False when no index exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ProjectConfig(
                project_path=Path("/project"),
                project_name="project",
                project_hash="abc123",
                storage_dir=Path(tmpdir)
            )
            assert config.is_indexed() is False

    def test_is_indexed_true_when_index_exists(self):
        """Test is_indexed returns True when index exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            index_dir = storage / "index"
            index_dir.mkdir(parents=True)
            (index_dir / "code.index").touch()

            config = ProjectConfig(
                project_path=Path("/project"),
                project_name="project",
                project_hash="abc123",
                storage_dir=storage
            )
            assert config.is_indexed() is True


@pytest.mark.unit
class TestConfig:
    """Tests for main Config class."""

    def test_default_storage_dir(self):
        """Test default storage directory is in home."""
        config = Config()
        assert str(config.storage_dir).endswith(".claude_code_search")

    def test_default_threshold(self):
        """Test default search threshold."""
        config = Config()
        assert config.default_threshold == 0.4

    def test_default_max_results(self):
        """Test default max results."""
        config = Config()
        assert config.max_results == 20

    def test_nested_config_objects(self):
        """Test Config has nested config objects."""
        config = Config()
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.index, IndexConfig)
        assert isinstance(config.watch, WatchConfig)
        assert isinstance(config.output, OutputConfig)

    def test_get_config_path_default(self):
        """Test default config path."""
        path = Config.get_config_path()
        assert path.name == "config.toml"
        assert "csearch" in str(path)

    def test_get_config_path_with_xdg(self, monkeypatch):
        """Test config path respects XDG_CONFIG_HOME."""
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        path = Config.get_config_path()
        assert path == Path("/custom/config/csearch/config.toml")

    def test_load_with_env_override(self, monkeypatch):
        """Test storage dir can be overridden by environment when no config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage"
            config_home = Path(tmpdir) / "config"  # Empty config dir (no config.toml)
            config_home.mkdir()

            # Set both XDG_CONFIG_HOME and CODE_SEARCH_STORAGE
            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(storage))
            get_config.cache_clear()

            config = Config.load()
            assert str(config.storage_dir) == str(storage)
            get_config.cache_clear()

    def test_load_creates_storage_dir(self, monkeypatch):
        """Test load creates storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "new_storage"
            config_home = Path(tmpdir) / "config"  # Empty config dir (no config.toml)
            config_home.mkdir()

            monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(storage))
            get_config.cache_clear()

            config = Config.load()
            assert storage.exists()
            get_config.cache_clear()

    def test_load_from_toml_file(self, monkeypatch):
        """Test loading config from TOML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "csearch"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.toml"

            config_content = """
[general]
default_threshold = 0.6
max_results = 50

[model]
device = "cuda"
batch_size = 64

[index]
max_file_size_kb = 2048

[watch]
debounce_ms = 3000
auto_start = true

[output]
context_lines = 5
show_score = true
"""
            config_file.write_text(config_content)

            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(Path(tmpdir) / "storage"))
            get_config.cache_clear()

            config = Config.load()

            assert config.default_threshold == 0.6
            assert config.max_results == 50
            assert config.model.device == "cuda"
            assert config.model.batch_size == 64
            assert config.index.max_file_size_kb == 2048
            assert config.watch.debounce_ms == 3000
            assert config.watch.auto_start is True
            assert config.output.context_lines == 5
            assert config.output.show_score is True

            get_config.cache_clear()

    def test_save_config(self, monkeypatch):
        """Test saving config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "csearch"
            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(Path(tmpdir) / "storage"))

            config = Config()
            config.default_threshold = 0.7
            config.max_results = 30
            config.model.device = "mps"
            config.save()

            # Verify file was created
            config_file = config_dir / "config.toml"
            assert config_file.exists()

            # Verify content
            content = config_file.read_text()
            assert "default_threshold = 0.7" in content
            assert "max_results = 30" in content
            assert 'device = "mps"' in content

    def test_get_project_config(self):
        """Test get_project_config method."""
        config = Config()
        project_config = config.get_project_config(Path("/home/user/project"))

        assert isinstance(project_config, ProjectConfig)
        assert project_config.project_name == "project"

    def test_models_dir_property(self):
        """Test models_dir property."""
        config = Config()
        assert config.models_dir == config.storage_dir / "models"

    def test_projects_dir_property(self):
        """Test projects_dir property."""
        config = Config()
        assert config.projects_dir == config.storage_dir / "projects"


@pytest.mark.unit
class TestGetConfig:
    """Tests for get_config function."""

    def test_returns_config_instance(self, monkeypatch):
        """Test get_config returns Config instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("CODE_SEARCH_STORAGE", tmpdir)
            get_config.cache_clear()
            config = get_config()
            assert isinstance(config, Config)
            get_config.cache_clear()

    def test_caches_result(self, monkeypatch):
        """Test get_config caches the result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("CODE_SEARCH_STORAGE", tmpdir)
            get_config.cache_clear()

            config1 = get_config()
            config2 = get_config()

            assert config1 is config2
            get_config.cache_clear()


@pytest.mark.unit
class TestConfigEdgeCases:
    """Tests for edge cases and error handling."""

    def test_load_with_invalid_toml(self, monkeypatch):
        """Test loading with invalid TOML falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "csearch"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.toml"
            config_file.write_text("invalid { toml content")

            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(Path(tmpdir) / "storage"))
            get_config.cache_clear()

            config = Config.load()
            # Should use defaults
            assert config.default_threshold == 0.4
            get_config.cache_clear()

    def test_load_with_partial_toml(self, monkeypatch):
        """Test loading with partial TOML preserves defaults for missing values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "csearch"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.toml"
            config_file.write_text("[general]\nmax_results = 100\n")

            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            monkeypatch.setenv("CODE_SEARCH_STORAGE", str(Path(tmpdir) / "storage"))
            get_config.cache_clear()

            config = Config.load()
            # Custom value
            assert config.max_results == 100
            # Default value preserved
            assert config.default_threshold == 0.4
            get_config.cache_clear()

    def test_storage_dir_with_tilde(self, monkeypatch):
        """Test storage_dir with tilde expansion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "csearch"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.toml"
            config_file.write_text('[general]\nstorage_dir = "~/custom_storage"\n')

            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            get_config.cache_clear()

            config = Config.load()
            # Path should be expanded
            assert "~" not in str(config.storage_dir)
            get_config.cache_clear()

    def test_project_hash_is_deterministic(self):
        """Test that project hash is deterministic for same path."""
        base_storage = Path("/tmp/storage")
        path = Path("/some/project/path")

        hashes = [
            ProjectConfig.from_path(path, base_storage).project_hash
            for _ in range(5)
        ]

        assert len(set(hashes)) == 1, "All hashes should be identical"

    def test_project_hash_length(self):
        """Test project hash has expected length."""
        config = ProjectConfig.from_path(Path("/project"), Path("/storage"))
        assert len(config.project_hash) == 16
