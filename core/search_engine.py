"""Search engine - unified interface for semantic code search."""

import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from core.config import Config, ProjectConfig, get_config
from core.project import ProjectManager

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    file_path: str
    relative_path: str
    line_start: int
    line_end: int
    content: str
    chunk_type: str
    name: Optional[str]
    score: float
    language: Optional[str] = None
    chunk_id: Optional[str] = None
    parent_name: Optional[str] = None
    docstring: Optional[str] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.relative_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "score": round(self.score, 3),
            "chunk_type": self.chunk_type,
            "name": self.name,
            "language": self.language,
            "content": self.content,
        }


@dataclass
class IndexResult:
    """Result of an indexing operation."""
    success: bool
    files_added: int = 0
    files_removed: int = 0
    files_modified: int = 0
    chunks_added: int = 0
    chunks_removed: int = 0
    time_taken: float = 0.0
    error: Optional[str] = None
    was_incremental: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "files_added": self.files_added,
            "files_removed": self.files_removed,
            "files_modified": self.files_modified,
            "chunks_added": self.chunks_added,
            "chunks_removed": self.chunks_removed,
            "time_taken": round(self.time_taken, 2),
            "was_incremental": self.was_incremental,
            "error": self.error,
        }


class SearchEngine:
    """Unified search engine for semantic code search."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize search engine.

        Args:
            config: Configuration instance. Uses global config if not provided.
        """
        self.config = config or get_config()
        self.project_manager = ProjectManager(self.config)
        self._embedder = None
        self._index_managers: Dict[str, Any] = {}
        self._searchers: Dict[str, Any] = {}
        self._chunkers: Dict[str, Any] = {}

    @property
    def embedder(self):
        """Lazy-load embedder."""
        if self._embedder is None:
            from embeddings.embedder import CodeEmbedder
            cache_dir = self.config.models_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._embedder = CodeEmbedder(cache_dir=str(cache_dir))
            logger.info("Embedder initialized")
        return self._embedder

    def _get_index_manager(self, project_config: ProjectConfig):
        """Get or create index manager for a project."""
        key = str(project_config.storage_dir)
        if key not in self._index_managers:
            from search.indexer import CodeIndexManager
            self.project_manager.ensure_project_dirs(project_config)
            self._index_managers[key] = CodeIndexManager(str(project_config.index_dir))
        return self._index_managers[key]

    def _get_searcher(self, project_config: ProjectConfig):
        """Get or create searcher for a project."""
        key = str(project_config.storage_dir)
        if key not in self._searchers:
            from search.searcher import IntelligentSearcher
            index_manager = self._get_index_manager(project_config)
            self._searchers[key] = IntelligentSearcher(index_manager, self.embedder)
        return self._searchers[key]

    def _get_chunker(self, project_path: Path):
        """Get or create chunker for a project."""
        key = str(project_path)
        if key not in self._chunkers:
            from chunking.multi_language_chunker import MultiLanguageChunker
            self._chunkers[key] = MultiLanguageChunker(str(project_path))
        return self._chunkers[key]

    def search(
        self,
        query: str,
        project_path: Optional[Path] = None,
        max_results: int = 10,
        threshold: float = 0.0,
        file_pattern: Optional[str] = None,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
        include_context: bool = True,
    ) -> List[SearchResult]:
        """Perform semantic code search.

        Args:
            query: Natural language search query.
            project_path: Path to project. Uses current directory if not provided.
            max_results: Maximum number of results to return.
            threshold: Minimum similarity score threshold (0-1).
            file_pattern: Glob pattern to filter files.
            language: Filter by programming language.
            chunk_type: Filter by chunk type (function, class, method).
            include_context: Include context information in results.

        Returns:
            List of SearchResult objects.
        """
        if project_path is None:
            project_path = Path.cwd()

        project_config = self.project_manager.get_project_config(project_path)

        if not project_config.is_indexed():
            logger.warning(f"Project not indexed: {project_path}")
            return []

        searcher = self._get_searcher(project_config)

        # Build filters
        filters = {}
        if file_pattern:
            filters["file_pattern"] = [file_pattern]
        if chunk_type:
            filters["chunk_type"] = chunk_type

        # Perform search
        context_depth = 1 if include_context else 0
        raw_results = searcher.search(
            query=query,
            k=max_results,
            search_mode="semantic",
            context_depth=context_depth,
            filters=filters if filters else None
        )

        # Convert to our SearchResult format
        results = []
        for result in raw_results:
            # Apply threshold filter
            if threshold > 0 and result.similarity_score < threshold:
                continue

            # Apply language filter
            if language:
                # Infer language from file extension
                ext = Path(result.relative_path).suffix.lower()
                lang_map = {
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".tsx": "typescript",
                    ".jsx": "javascript",
                    ".go": "go",
                    ".java": "java",
                    ".rs": "rust",
                    ".c": "c",
                    ".cpp": "cpp",
                    ".h": "c",
                    ".hpp": "cpp",
                    ".cs": "csharp",
                    ".svelte": "svelte",
                    ".md": "markdown",
                }
                file_lang = lang_map.get(ext, "unknown")
                if file_lang.lower() != language.lower():
                    continue

            search_result = SearchResult(
                file_path=result.file_path,
                relative_path=result.relative_path,
                line_start=result.start_line,
                line_end=result.end_line,
                content=result.content_preview or "",
                chunk_type=result.chunk_type,
                name=result.name,
                score=result.similarity_score,
                language=self._infer_language(result.relative_path),
                chunk_id=result.chunk_id,
                parent_name=result.parent_name,
                docstring=result.docstring,
                tags=result.tags,
            )
            results.append(search_result)

        return results

    def search_exact(
        self,
        pattern: str,
        project_path: Optional[Path] = None,
        file_pattern: Optional[str] = None,
    ) -> List[SearchResult]:
        """Perform exact text search using ripgrep.

        Args:
            pattern: Exact pattern to search for.
            project_path: Path to project. Uses current directory if not provided.
            file_pattern: Glob pattern to filter files.

        Returns:
            List of SearchResult objects.
        """
        if project_path is None:
            project_path = Path.cwd()

        # Try ripgrep first, fall back to grep
        try:
            cmd = ["rg", "--line-number", "--no-heading", "--with-filename"]
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
            cmd.extend([pattern, str(project_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
        except FileNotFoundError:
            # ripgrep not available, fall back to grep
            cmd = ["grep", "-rn"]
            if file_pattern:
                cmd.extend(["--include", file_pattern])
            cmd.extend([pattern, str(project_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("Exact search timed out")
            return []

        # Parse output
        results = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            try:
                # Format: file:line:content
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    content = parts[2]

                    rel_path = file_path
                    try:
                        rel_path = str(Path(file_path).relative_to(project_path))
                    except ValueError:
                        pass

                    results.append(SearchResult(
                        file_path=file_path,
                        relative_path=rel_path,
                        line_start=line_num,
                        line_end=line_num,
                        content=content,
                        chunk_type="line",
                        name=None,
                        score=1.0,
                        language=self._infer_language(file_path),
                    ))
            except Exception:
                continue

        return results

    def search_hybrid(
        self,
        semantic_query: str,
        exact_pattern: str,
        project_path: Optional[Path] = None,
        max_results: int = 10,
    ) -> List[SearchResult]:
        """Hybrid search: semantic search filtered by exact pattern.

        Args:
            semantic_query: Semantic search query.
            exact_pattern: Exact pattern that results must contain.
            project_path: Path to project.
            max_results: Maximum results to return.

        Returns:
            List of SearchResult objects that match both criteria.
        """
        # First, get semantic results
        semantic_results = self.search(
            query=semantic_query,
            project_path=project_path,
            max_results=max_results * 3,  # Get more to filter
        )

        # Filter by exact pattern
        filtered = []
        for result in semantic_results:
            if exact_pattern.lower() in result.content.lower():
                filtered.append(result)
                if len(filtered) >= max_results:
                    break

        return filtered

    def index(
        self,
        project_path: Optional[Path] = None,
        force_full: bool = False,
        dry_run: bool = False,
    ) -> IndexResult:
        """Index a project directory.

        Args:
            project_path: Path to project. Uses current directory if not provided.
            force_full: Force full reindex even if incremental is possible.
            dry_run: Only show what would be indexed.

        Returns:
            IndexResult with statistics.
        """
        if project_path is None:
            project_path = Path.cwd()

        project_path = project_path.resolve()

        if not project_path.exists():
            return IndexResult(success=False, error=f"Path does not exist: {project_path}")

        if not project_path.is_dir():
            return IndexResult(success=False, error=f"Path is not a directory: {project_path}")

        project_config = self.project_manager.get_project_config(project_path)
        self.project_manager.ensure_project_dirs(project_config)

        if dry_run:
            return self._dry_run_index(project_path, project_config)

        start_time = time.time()

        try:
            from search.incremental_indexer import IncrementalIndexer
            from merkle.snapshot_manager import SnapshotManager

            index_manager = self._get_index_manager(project_config)
            chunker = self._get_chunker(project_path)
            snapshot_manager = SnapshotManager(str(project_config.snapshot_dir))

            incremental_indexer = IncrementalIndexer(
                indexer=index_manager,
                embedder=self.embedder,
                chunker=chunker,
                snapshot_manager=snapshot_manager,
            )

            result = incremental_indexer.incremental_index(
                str(project_path),
                project_config.project_name,
                force_full=force_full,
            )

            # Save project info
            self.project_manager.save_project_info(
                project_config,
                last_indexed=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )

            return IndexResult(
                success=result.success,
                files_added=result.files_added,
                files_removed=result.files_removed,
                files_modified=result.files_modified,
                chunks_added=result.chunks_added,
                chunks_removed=result.chunks_removed,
                time_taken=result.time_taken,
                was_incremental=not force_full and (result.files_modified > 0 or result.files_added > 0),
                error=result.error,
            )

        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            return IndexResult(
                success=False,
                time_taken=time.time() - start_time,
                error=str(e),
            )

    def _dry_run_index(self, project_path: Path, project_config: ProjectConfig) -> IndexResult:
        """Perform a dry run of indexing."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from merkle.merkle_dag import MerkleDAG

        chunker = MultiLanguageChunker(str(project_path))
        dag = MerkleDAG(str(project_path))
        dag.build()

        all_files = dag.get_all_files()
        supported_files = [f for f in all_files if chunker.is_supported(f)]

        return IndexResult(
            success=True,
            files_added=len(supported_files),
            chunks_added=0,  # Would need to chunk to know
            time_taken=0,
        )

    def get_status(self, project_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Get status of a project index.

        Args:
            project_path: Path to project. Uses current directory if not provided.

        Returns:
            Dictionary with status information, or None if not indexed.
        """
        if project_path is None:
            project_path = Path.cwd()

        project_config = self.project_manager.get_project_config(project_path)

        if not project_config.is_indexed():
            return None

        info = self.project_manager.get_project_info(project_config)
        if not info:
            return None

        # Add some extra info
        index_manager = self._get_index_manager(project_config)
        stats = index_manager.get_stats()

        return {
            "project_name": info.project_name,
            "project_path": info.project_path,
            "created_at": info.created_at,
            "last_indexed": info.last_indexed,
            "files_indexed": stats.get("files_indexed", 0),
            "chunks_indexed": stats.get("total_chunks", 0),
            "chunk_types": stats.get("chunk_types", {}),
            "top_folders": stats.get("top_folders", {}),
            "index_size_mb": round(info.index_size_bytes / (1024 * 1024), 2) if info.index_size_bytes else 0,
            "watcher_running": info.watcher_running,
            "watcher_pid": info.watcher_pid,
        }

    def clear(self, project_path: Optional[Path] = None) -> bool:
        """Clear index for a project.

        Args:
            project_path: Path to project. Uses current directory if not provided.

        Returns:
            True if cleared, False otherwise.
        """
        if project_path is None:
            project_path = Path.cwd()

        project_config = self.project_manager.get_project_config(project_path)
        return self.project_manager.remove_project(project_config)

    def clear_all(self) -> int:
        """Clear all indexed projects.

        Returns:
            Number of projects cleared.
        """
        return self.project_manager.remove_all_projects()

    def find_similar(
        self,
        chunk_id: str,
        project_path: Optional[Path] = None,
        max_results: int = 5,
    ) -> List[SearchResult]:
        """Find code similar to a given chunk.

        Args:
            chunk_id: ID of the chunk to find similar code for.
            project_path: Path to project.
            max_results: Maximum results to return.

        Returns:
            List of similar SearchResult objects.
        """
        if project_path is None:
            project_path = Path.cwd()

        project_config = self.project_manager.get_project_config(project_path)

        if not project_config.is_indexed():
            return []

        searcher = self._get_searcher(project_config)
        raw_results = searcher.find_similar_to_chunk(chunk_id, k=max_results)

        results = []
        for result in raw_results:
            search_result = SearchResult(
                file_path=result.file_path,
                relative_path=result.relative_path,
                line_start=result.start_line,
                line_end=result.end_line,
                content=result.content_preview or "",
                chunk_type=result.chunk_type,
                name=result.name,
                score=result.similarity_score,
                language=self._infer_language(result.relative_path),
                chunk_id=result.chunk_id,
            )
            results.append(search_result)

        return results

    def _infer_language(self, file_path: str) -> str:
        """Infer programming language from file path."""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".svelte": "svelte",
            ".md": "markdown",
        }
        return lang_map.get(ext, "unknown")
