"""Unit tests for project management module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.config import Config, ProjectConfig, get_config
from core.project import ProjectInfo, ProjectManager


@pytest.mark.unit
class TestProjectInfo:
    """Tests for ProjectInfo dataclass."""

    def test_default_values(self):
        """Test ProjectInfo default values."""
        info = ProjectInfo(
            project_name="test",
            project_path="/path/to/project",
            project_hash="abc123",
            created_at="2024-01-01T00:00:00"
        )
        assert info.last_indexed is None
        assert info.files_indexed == 0
        assert info.chunks_indexed == 0
        assert info.languages is None
        assert info.index_size_bytes == 0
        assert info.watcher_running is False
        assert info.watcher_pid is None
        assert info.is_fully_indexed is True

    def test_all_values(self):
        """Test ProjectInfo with all values set."""
        info = ProjectInfo(
            project_name="test",
            project_path="/path/to/project",
            project_hash="abc123",
            created_at="2024-01-01T00:00:00",
            last_indexed="2024-01-02T00:00:00",
            files_indexed=100,
            chunks_indexed=500,
            languages={"python": 400, "javascript": 100},
            index_size_bytes=1024000,
            watcher_running=True,
            watcher_pid=12345,
            is_fully_indexed=True
        )
        assert info.files_indexed == 100
        assert info.chunks_indexed == 500
        assert info.languages == {"python": 400, "javascript": 100}
        assert info.watcher_running is True
        assert info.watcher_pid == 12345

    def test_to_dict(self):
        """Test ProjectInfo to_dict conversion."""
        info = ProjectInfo(
            project_name="test",
            project_path="/path/to/project",
            project_hash="abc123",
            created_at="2024-01-01T00:00:00",
            files_indexed=50,
            is_fully_indexed=False
        )
        result = info.to_dict()

        assert result["project_name"] == "test"
        assert result["project_path"] == "/path/to/project"
        assert result["project_hash"] == "abc123"
        assert result["files_indexed"] == 50
        assert result["is_fully_indexed"] is False

    def test_to_dict_contains_all_fields(self):
        """Test to_dict includes all fields."""
        info = ProjectInfo(
            project_name="test",
            project_path="/path",
            project_hash="hash",
            created_at="2024-01-01"
        )
        result = info.to_dict()
        expected_keys = {
            "project_name", "project_path", "project_hash", "created_at",
            "last_indexed", "files_indexed", "chunks_indexed", "languages",
            "index_size_bytes", "watcher_running", "watcher_pid", "is_fully_indexed"
        }
        assert set(result.keys()) == expected_keys


@pytest.mark.unit
class TestProjectManager:
    """Tests for ProjectManager class."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config(self, temp_storage):
        """Create Config with temporary storage."""
        config = Config()
        config.storage_dir = temp_storage
        return config

    @pytest.fixture
    def manager(self, config):
        """Create ProjectManager with test config."""
        return ProjectManager(config)

    def test_init_with_config(self, config):
        """Test initialization with provided config."""
        manager = ProjectManager(config)
        assert manager.config is config

    def test_init_without_config(self, monkeypatch, temp_storage):
        """Test initialization without config uses global config."""
        monkeypatch.setenv("CODE_SEARCH_STORAGE", str(temp_storage))
        get_config.cache_clear()

        manager = ProjectManager()
        assert manager.config is not None
        get_config.cache_clear()

    def test_get_project_config(self, manager, temp_storage):
        """Test get_project_config returns ProjectConfig."""
        project_path = temp_storage / "my-project"
        project_path.mkdir()

        config = manager.get_project_config(project_path)

        assert isinstance(config, ProjectConfig)
        assert config.project_name == "my-project"

    def test_ensure_project_dirs_creates_directories(self, manager, temp_storage):
        """Test ensure_project_dirs creates all necessary directories."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)

        assert project_config.storage_dir.exists()
        assert project_config.index_dir.exists()
        assert project_config.snapshot_dir.exists()

    def test_save_project_info_creates_file(self, manager, temp_storage):
        """Test save_project_info creates project_info.json."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.save_project_info(project_config, files_indexed=100)

        assert project_config.project_info_file.exists()

        with open(project_config.project_info_file) as f:
            data = json.load(f)

        assert data["project_name"] == "project"
        assert data["files_indexed"] == 100
        assert "created_at" in data
        assert "last_updated" in data

    def test_save_project_info_updates_existing(self, manager, temp_storage):
        """Test save_project_info updates existing info."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        # First save
        manager.save_project_info(project_config, files_indexed=50)

        with open(project_config.project_info_file) as f:
            data1 = json.load(f)
        original_created_at = data1["created_at"]

        # Second save
        manager.save_project_info(project_config, files_indexed=100, chunks_indexed=500)

        with open(project_config.project_info_file) as f:
            data2 = json.load(f)

        # created_at should be preserved
        assert data2["created_at"] == original_created_at
        # New values should be updated
        assert data2["files_indexed"] == 100
        assert data2["chunks_indexed"] == 500

    def test_get_project_info_returns_none_when_not_exists(self, manager, temp_storage):
        """Test get_project_info returns None for non-existent project."""
        project_config = ProjectConfig(
            project_path=temp_storage / "nonexistent",
            project_name="nonexistent",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "nonexistent_abc123"
        )

        result = manager.get_project_info(project_config)
        assert result is None

    def test_get_project_info_returns_project_info(self, manager, temp_storage):
        """Test get_project_info returns ProjectInfo for existing project."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        # Create project info
        manager.save_project_info(project_config, files_indexed=75)

        result = manager.get_project_info(project_config)

        assert result is not None
        assert isinstance(result, ProjectInfo)
        assert result.project_name == "project"

    def test_get_project_info_includes_stats(self, manager, temp_storage):
        """Test get_project_info includes stats from stats.json."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)
        manager.save_project_info(project_config)

        # Create stats.json
        stats_file = project_config.index_dir / "stats.json"
        with open(stats_file, "w") as f:
            json.dump({
                "files_indexed": 150,
                "total_chunks": 800,
                "chunk_types": {"function": 500, "class": 300}
            }, f)

        result = manager.get_project_info(project_config)

        assert result.files_indexed == 150
        assert result.chunks_indexed == 800
        assert result.languages == {"function": 500, "class": 300}

    def test_get_project_info_detects_incomplete_index(self, manager, temp_storage):
        """Test get_project_info detects incomplete index."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.save_project_info(project_config)
        # No code.index file created

        result = manager.get_project_info(project_config)

        assert result is not None
        assert result.is_fully_indexed is False

    def test_get_project_info_detects_complete_index(self, manager, temp_storage):
        """Test get_project_info detects complete index."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)
        manager.save_project_info(project_config)

        # Create index file
        (project_config.index_dir / "code.index").write_bytes(b"dummy index data")

        result = manager.get_project_info(project_config)

        assert result is not None
        assert result.is_fully_indexed is True
        assert result.index_size_bytes > 0

    def test_get_project_info_handles_watcher_pid(self, manager, temp_storage):
        """Test get_project_info detects watcher status."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)
        manager.save_project_info(project_config)

        # Create watcher PID file with non-existent PID
        project_config.watcher_pid_file.write_text("99999999")

        result = manager.get_project_info(project_config)

        # Should detect process not running and clean up
        assert result.watcher_running is False
        assert result.watcher_pid is None

    def test_list_projects_empty(self, manager, temp_storage):
        """Test list_projects returns empty list when no projects."""
        result = manager.list_projects()
        assert result == []

    def test_list_projects_returns_all_projects(self, manager, temp_storage):
        """Test list_projects returns all projects."""
        # Create two projects
        for name in ["project1", "project2"]:
            project_path = temp_storage / name
            project_path.mkdir()
            project_config = manager.get_project_config(project_path)
            manager.save_project_info(project_config)
            # Create index file to make it complete
            project_config.index_dir.mkdir(parents=True, exist_ok=True)
            (project_config.index_dir / "code.index").touch()

        result = manager.list_projects()

        assert len(result) == 2
        names = [p.project_name for p in result]
        assert "project1" in names
        assert "project2" in names

    def test_list_projects_skips_invalid_projects(self, manager, temp_storage):
        """Test list_projects skips projects with invalid data."""
        # Create valid project
        project_path = temp_storage / "valid"
        project_path.mkdir()
        project_config = manager.get_project_config(project_path)
        manager.save_project_info(project_config)
        project_config.index_dir.mkdir(parents=True, exist_ok=True)
        (project_config.index_dir / "code.index").touch()

        # Create invalid project directory
        invalid_dir = manager.config.projects_dir / "invalid_abc123"
        invalid_dir.mkdir(parents=True)
        (invalid_dir / "project_info.json").write_text("invalid json")

        result = manager.list_projects()

        # Should only return valid project
        assert len(result) == 1
        assert result[0].project_name == "valid"

    def test_find_project_for_path_direct(self, manager, temp_storage):
        """Test find_project_for_path finds direct project."""
        project_path = temp_storage / "project"
        project_path.mkdir()
        project_config = manager.get_project_config(project_path)
        manager.ensure_project_dirs(project_config)
        (project_config.index_dir / "code.index").touch()

        result = manager.find_project_for_path(project_path)

        assert result is not None
        assert result.project_path == project_path.resolve()

    def test_find_project_for_path_subdirectory(self, manager, temp_storage):
        """Test find_project_for_path finds project from subdirectory."""
        project_path = temp_storage / "project"
        subdir = project_path / "src" / "module"
        subdir.mkdir(parents=True)

        project_config = manager.get_project_config(project_path)
        manager.ensure_project_dirs(project_config)
        (project_config.index_dir / "code.index").touch()

        result = manager.find_project_for_path(subdir)

        assert result is not None
        assert result.project_path == project_path.resolve()

    def test_find_project_for_path_not_found(self, manager, temp_storage):
        """Test find_project_for_path returns None when not found."""
        path = temp_storage / "nonexistent"
        path.mkdir()

        result = manager.find_project_for_path(path)
        assert result is None

    def test_remove_project_success(self, manager, temp_storage):
        """Test remove_project successfully removes project."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)
        manager.save_project_info(project_config)
        (project_config.index_dir / "code.index").touch()

        assert project_config.storage_dir.exists()

        result = manager.remove_project(project_config)

        assert result is True
        assert not project_config.storage_dir.exists()

    def test_remove_project_nonexistent(self, manager, temp_storage):
        """Test remove_project returns False for non-existent project."""
        project_config = ProjectConfig(
            project_path=temp_storage / "nonexistent",
            project_name="nonexistent",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "nonexistent_abc123"
        )

        result = manager.remove_project(project_config)
        assert result is False

    def test_remove_all_projects(self, manager, temp_storage):
        """Test remove_all_projects removes all projects."""
        # Create multiple projects
        for name in ["p1", "p2", "p3"]:
            project_path = temp_storage / name
            project_path.mkdir()
            project_config = manager.get_project_config(project_path)
            manager.ensure_project_dirs(project_config)
            manager.save_project_info(project_config)

        # Verify they exist
        assert len(list(manager.config.projects_dir.iterdir())) == 3

        result = manager.remove_all_projects()

        assert result == 3
        assert len(list(manager.config.projects_dir.iterdir())) == 0

    def test_remove_all_projects_empty(self, manager, temp_storage):
        """Test remove_all_projects returns 0 when no projects."""
        result = manager.remove_all_projects()
        assert result == 0


@pytest.mark.unit
class TestProjectManagerEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_storage):
        """Create ProjectManager with test config."""
        config = Config()
        config.storage_dir = temp_storage
        return ProjectManager(config)

    def test_save_project_info_handles_corrupted_existing(self, manager, temp_storage):
        """Test save_project_info handles corrupted existing file."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)

        # Create corrupted file
        project_config.project_info_file.write_text("not json")

        # Should not raise, should overwrite
        manager.save_project_info(project_config, files_indexed=50)

        with open(project_config.project_info_file) as f:
            data = json.load(f)
        assert data["files_indexed"] == 50

    def test_get_project_info_handles_missing_fields(self, manager, temp_storage):
        """Test get_project_info handles missing fields in JSON."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)

        # Create minimal project info
        project_config.project_info_file.write_text(json.dumps({
            "project_name": "project",
            "project_path": str(temp_storage / "project"),
            "project_hash": "abc123",
            "created_at": "2024-01-01"
        }))

        result = manager.get_project_info(project_config)

        assert result is not None
        assert result.files_indexed == 0
        assert result.chunks_indexed == 0

    def test_list_projects_handles_nonexistent_project_paths(self, manager, temp_storage):
        """Test list_projects handles projects with deleted paths."""
        # Create project with a path that doesn't exist
        project_dir = manager.config.projects_dir / "deleted_abc123"
        project_dir.mkdir(parents=True)
        (project_dir / "project_info.json").write_text(json.dumps({
            "project_name": "deleted",
            "project_path": "/nonexistent/path",
            "project_hash": "abc123",
            "created_at": "2024-01-01"
        }))

        result = manager.list_projects()

        # Should skip the project with non-existent path
        assert len(result) == 0

    def test_get_project_info_handles_watcher_pid_not_number(self, manager, temp_storage):
        """Test get_project_info handles non-numeric PID file."""
        project_config = ProjectConfig(
            project_path=temp_storage / "project",
            project_name="project",
            project_hash="abc123",
            storage_dir=temp_storage / "projects" / "project_abc123"
        )

        manager.ensure_project_dirs(project_config)
        manager.save_project_info(project_config)
        project_config.watcher_pid_file.write_text("not a number")

        result = manager.get_project_info(project_config)

        assert result is not None
        assert result.watcher_running is False
        assert result.watcher_pid is None
