"""Project management for csearch."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config import Config, ProjectConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    """Information about an indexed project."""
    project_name: str
    project_path: str
    project_hash: str
    created_at: str
    last_indexed: Optional[str] = None
    files_indexed: int = 0
    chunks_indexed: int = 0
    languages: Optional[Dict[str, int]] = None
    index_size_bytes: int = 0
    watcher_running: bool = False
    watcher_pid: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "project_hash": self.project_hash,
            "created_at": self.created_at,
            "last_indexed": self.last_indexed,
            "files_indexed": self.files_indexed,
            "chunks_indexed": self.chunks_indexed,
            "languages": self.languages,
            "index_size_bytes": self.index_size_bytes,
            "watcher_running": self.watcher_running,
            "watcher_pid": self.watcher_pid,
        }


class ProjectManager:
    """Manages projects and their configurations."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize project manager.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self.config = config or get_config()

    def get_project_config(self, project_path: Path) -> ProjectConfig:
        """Get configuration for a project.

        Args:
            project_path: Path to the project directory.

        Returns:
            ProjectConfig for the project.
        """
        return self.config.get_project_config(project_path)

    def ensure_project_dirs(self, project_config: ProjectConfig) -> None:
        """Ensure project directories exist.

        Args:
            project_config: Project configuration.
        """
        project_config.storage_dir.mkdir(parents=True, exist_ok=True)
        project_config.index_dir.mkdir(parents=True, exist_ok=True)
        project_config.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_project_info(self, project_config: ProjectConfig, **kwargs) -> None:
        """Save project information.

        Args:
            project_config: Project configuration.
            **kwargs: Additional info to save.
        """
        self.ensure_project_dirs(project_config)

        info = {
            "project_name": project_config.project_name,
            "project_path": str(project_config.project_path),
            "project_hash": project_config.project_hash,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }

        # Update with existing info if present
        if project_config.project_info_file.exists():
            try:
                with open(project_config.project_info_file) as f:
                    existing = json.load(f)
                    # Keep created_at from existing
                    if "created_at" in existing:
                        info["created_at"] = existing["created_at"]
                    # Update with new values
                    existing.update(info)
                    info = existing
            except Exception:
                pass

        info["last_updated"] = datetime.now().isoformat()

        with open(project_config.project_info_file, "w") as f:
            json.dump(info, f, indent=2)

    def get_project_info(self, project_config: ProjectConfig) -> Optional[ProjectInfo]:
        """Get project information.

        Args:
            project_config: Project configuration.

        Returns:
            ProjectInfo if project exists, None otherwise.
        """
        if not project_config.project_info_file.exists():
            return None

        try:
            with open(project_config.project_info_file) as f:
                data = json.load(f)

            # Load stats if available
            stats_file = project_config.index_dir / "stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                    data["files_indexed"] = stats.get("files_indexed", 0)
                    data["chunks_indexed"] = stats.get("total_chunks", 0)
                    data["languages"] = stats.get("chunk_types", {})

            # Calculate index size
            index_file = project_config.index_dir / "code.index"
            if index_file.exists():
                data["index_size_bytes"] = index_file.stat().st_size

            # Check watcher status
            data["watcher_running"] = False
            data["watcher_pid"] = None
            if project_config.watcher_pid_file.exists():
                try:
                    pid = int(project_config.watcher_pid_file.read_text().strip())
                    # Check if process is running
                    import os
                    try:
                        os.kill(pid, 0)
                        data["watcher_running"] = True
                        data["watcher_pid"] = pid
                    except OSError:
                        # Process not running, clean up PID file
                        project_config.watcher_pid_file.unlink(missing_ok=True)
                except Exception:
                    pass

            return ProjectInfo(**{
                k: data.get(k) for k in ProjectInfo.__dataclass_fields__.keys()
                if k in data
            })
        except Exception as e:
            logger.warning(f"Failed to load project info: {e}")
            return None

    def list_projects(self) -> List[ProjectInfo]:
        """List all indexed projects.

        Returns:
            List of ProjectInfo for all indexed projects.
        """
        projects = []

        if not self.config.projects_dir.exists():
            return projects

        for project_dir in self.config.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            info_file = project_dir / "project_info.json"
            if not info_file.exists():
                continue

            try:
                with open(info_file) as f:
                    data = json.load(f)

                # Create a temporary ProjectConfig to get full info
                project_path = Path(data.get("project_path", ""))
                if project_path.exists():
                    config = self.get_project_config(project_path)
                    info = self.get_project_info(config)
                    if info:
                        projects.append(info)
            except Exception as e:
                logger.warning(f"Failed to load project from {project_dir}: {e}")

        return projects

    def find_project_for_path(self, path: Path) -> Optional[ProjectConfig]:
        """Find a project that contains the given path.

        Args:
            path: Path to find project for.

        Returns:
            ProjectConfig if found, None otherwise.
        """
        path = path.resolve()

        # First, check if path itself is an indexed project
        config = self.get_project_config(path)
        if config.is_indexed():
            return config

        # Check parent directories
        for parent in path.parents:
            config = self.get_project_config(parent)
            if config.is_indexed():
                return config

        return None

    def remove_project(self, project_config: ProjectConfig) -> bool:
        """Remove a project and all its data.

        Args:
            project_config: Project configuration.

        Returns:
            True if removed, False otherwise.
        """
        import shutil

        if not project_config.storage_dir.exists():
            return False

        try:
            shutil.rmtree(project_config.storage_dir)
            logger.info(f"Removed project: {project_config.project_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove project: {e}")
            return False

    def remove_all_projects(self) -> int:
        """Remove all indexed projects.

        Returns:
            Number of projects removed.
        """
        import shutil

        count = 0
        if not self.config.projects_dir.exists():
            return count

        for project_dir in self.config.projects_dir.iterdir():
            if project_dir.is_dir():
                try:
                    shutil.rmtree(project_dir)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to remove {project_dir}: {e}")

        return count
