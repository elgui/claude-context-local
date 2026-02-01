"""Centralized configuration management for csearch."""

import os
import hashlib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache


@dataclass
class ModelConfig:
    """Configuration for embedding model."""
    name: str = "google/embeddinggemma-300m"
    device: str = "auto"  # auto, cuda, mps, cpu
    batch_size: int = 32


@dataclass
class IndexConfig:
    """Configuration for indexing behavior."""
    excluded_dirs: List[str] = field(default_factory=lambda: [
        "node_modules", ".venv", "venv", "__pycache__", ".git",
        "dist", "build", ".next", "target", ".cache", ".tox",
        "egg-info", ".eggs", ".mypy_cache", ".pytest_cache",
        ".coverage", "htmlcov", ".hypothesis", ".ruff_cache"
    ])
    excluded_extensions: List[str] = field(default_factory=lambda: [
        ".min.js", ".map", ".lock", ".pyc", ".pyo", ".so", ".dylib",
        ".exe", ".dll", ".bin", ".dat", ".db", ".sqlite", ".sqlite3"
    ])
    max_file_size_kb: int = 1024


@dataclass
class WatchConfig:
    """Configuration for file watching."""
    debounce_ms: int = 2000
    auto_start: bool = False


@dataclass
class OutputConfig:
    """Configuration for output formatting."""
    context_lines: int = 0
    show_score: bool = False
    truncate_lines: int = 120
    color: str = "auto"  # auto, always, never


@dataclass
class ProjectConfig:
    """Configuration for a specific project."""
    project_path: Path
    project_name: str
    project_hash: str
    storage_dir: Path

    @classmethod
    def from_path(cls, project_path: Path, base_storage_dir: Path) -> "ProjectConfig":
        """Create project config from a path."""
        project_path = project_path.resolve()
        project_name = project_path.name
        project_hash = hashlib.sha256(str(project_path).encode()).hexdigest()[:16]
        storage_dir = base_storage_dir / "projects" / f"{project_name}_{project_hash}"
        return cls(
            project_path=project_path,
            project_name=project_name,
            project_hash=project_hash,
            storage_dir=storage_dir
        )

    @property
    def index_dir(self) -> Path:
        """Get the index directory for this project."""
        return self.storage_dir / "index"

    @property
    def snapshot_dir(self) -> Path:
        """Get the snapshot directory for this project."""
        return self.storage_dir / "snapshots"

    @property
    def project_info_file(self) -> Path:
        """Get the project info file path."""
        return self.storage_dir / "project_info.json"

    @property
    def watcher_pid_file(self) -> Path:
        """Get the watcher PID file path."""
        return self.storage_dir / "watcher.pid"

    @property
    def lock_file(self) -> Path:
        """Get the index lock file path."""
        return self.storage_dir / "index.lock"

    def is_indexed(self) -> bool:
        """Check if this project has an index."""
        index_file = self.index_dir / "code.index"
        return index_file.exists()


@dataclass
class Config:
    """Main configuration class for csearch."""
    storage_dir: Path = field(default_factory=lambda: Path.home() / ".claude_code_search")
    default_threshold: float = 0.4
    max_results: int = 20
    model: ModelConfig = field(default_factory=ModelConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    watch: WatchConfig = field(default_factory=WatchConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the configuration file path."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "csearch" / "config.toml"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file, environment, and defaults."""
        config = cls()

        # Override storage dir from environment
        if storage_env := os.environ.get("CODE_SEARCH_STORAGE"):
            config.storage_dir = Path(storage_env)

        # Load from config file if it exists
        config_path = cls.get_config_path()
        if config_path.exists():
            config = cls._load_from_toml(config_path, config)

        # Ensure storage directory exists
        config.storage_dir.mkdir(parents=True, exist_ok=True)

        return config

    @classmethod
    def _load_from_toml(cls, config_path: Path, defaults: "Config") -> "Config":
        """Load configuration from TOML file."""
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            # Update defaults with loaded values
            general = data.get("general", {})
            if "storage_dir" in general:
                defaults.storage_dir = Path(general["storage_dir"]).expanduser()
            if "default_threshold" in general:
                defaults.default_threshold = float(general["default_threshold"])
            if "max_results" in general:
                defaults.max_results = int(general["max_results"])

            # Model config
            model_data = data.get("model", {})
            if "name" in model_data:
                defaults.model.name = model_data["name"]
            if "device" in model_data:
                defaults.model.device = model_data["device"]
            if "batch_size" in model_data:
                defaults.model.batch_size = int(model_data["batch_size"])

            # Index config
            index_data = data.get("index", {})
            if "excluded_dirs" in index_data:
                defaults.index.excluded_dirs = list(index_data["excluded_dirs"])
            if "excluded_extensions" in index_data:
                defaults.index.excluded_extensions = list(index_data["excluded_extensions"])
            if "max_file_size_kb" in index_data:
                defaults.index.max_file_size_kb = int(index_data["max_file_size_kb"])

            # Watch config
            watch_data = data.get("watch", {})
            if "debounce_ms" in watch_data:
                defaults.watch.debounce_ms = int(watch_data["debounce_ms"])
            if "auto_start" in watch_data:
                defaults.watch.auto_start = bool(watch_data["auto_start"])

            # Output config
            output_data = data.get("output", {})
            if "context_lines" in output_data:
                defaults.output.context_lines = int(output_data["context_lines"])
            if "show_score" in output_data:
                defaults.output.show_score = bool(output_data["show_score"])
            if "truncate_lines" in output_data:
                defaults.output.truncate_lines = int(output_data["truncate_lines"])
            if "color" in output_data:
                defaults.output.color = output_data["color"]

            return defaults
        except Exception:
            # If parsing fails, return defaults
            return defaults

    def save(self) -> None:
        """Save current configuration to file."""
        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        toml_content = f'''# csearch configuration file

[general]
storage_dir = "{self.storage_dir}"
default_threshold = {self.default_threshold}
max_results = {self.max_results}
color = "{self.output.color}"

[model]
name = "{self.model.name}"
device = "{self.model.device}"
batch_size = {self.model.batch_size}

[index]
excluded_dirs = {self.index.excluded_dirs}
excluded_extensions = {self.index.excluded_extensions}
max_file_size_kb = {self.index.max_file_size_kb}

[watch]
debounce_ms = {self.watch.debounce_ms}
auto_start = {"true" if self.watch.auto_start else "false"}

[output]
context_lines = {self.output.context_lines}
show_score = {"true" if self.output.show_score else "false"}
truncate_lines = {self.output.truncate_lines}
'''
        with open(config_path, "w") as f:
            f.write(toml_content)

    def get_project_config(self, project_path: Path) -> ProjectConfig:
        """Get configuration for a specific project."""
        return ProjectConfig.from_path(project_path, self.storage_dir)

    @property
    def models_dir(self) -> Path:
        """Get the models cache directory."""
        return self.storage_dir / "models"

    @property
    def projects_dir(self) -> Path:
        """Get the projects directory."""
        return self.storage_dir / "projects"


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config.load()
