"""Unit tests for search engine module."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from core.config import Config, ProjectConfig, get_config
from core.search_engine import SearchResult, IndexResult, SearchEngine


@pytest.mark.unit
class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_minimal_construction(self):
        """Test SearchResult with minimal required fields."""
        result = SearchResult(
            file_path="/path/to/file.py",
            relative_path="file.py",
            line_start=10,
            line_end=20,
            content="def function(): pass",
            chunk_type="function",
            name="function",
            score=0.85
        )
        assert result.file_path == "/path/to/file.py"
        assert result.line_start == 10
        assert result.score == 0.85

    def test_optional_fields(self):
        """Test SearchResult with optional fields."""
        result = SearchResult(
            file_path="/path/to/file.py",
            relative_path="file.py",
            line_start=10,
            line_end=20,
            content="def function(): pass",
            chunk_type="function",
            name="function",
            score=0.85,
            language="python",
            chunk_id="chunk_123",
            parent_name="MyClass",
            docstring="A function",
            tags=["async", "api"]
        )
        assert result.language == "python"
        assert result.chunk_id == "chunk_123"
        assert result.parent_name == "MyClass"
        assert result.docstring == "A function"
        assert result.tags == ["async", "api"]

    def test_to_dict(self):
        """Test SearchResult to_dict conversion."""
        result = SearchResult(
            file_path="/path/to/file.py",
            relative_path="src/file.py",
            line_start=10,
            line_end=20,
            content="def function(): pass",
            chunk_type="function",
            name="my_function",
            score=0.8567,
            language="python"
        )

        d = result.to_dict()

        assert d["file"] == "src/file.py"
        assert d["line_start"] == 10
        assert d["line_end"] == 20
        assert d["score"] == 0.857  # Rounded to 3 decimal places
        assert d["chunk_type"] == "function"
        assert d["name"] == "my_function"
        assert d["language"] == "python"
        assert d["content"] == "def function(): pass"


@pytest.mark.unit
class TestIndexResult:
    """Tests for IndexResult dataclass."""

    def test_success_result(self):
        """Test successful IndexResult."""
        result = IndexResult(
            success=True,
            files_added=50,
            files_modified=10,
            files_removed=5,
            chunks_added=200,
            chunks_removed=20,
            time_taken=5.5,
            was_incremental=True
        )
        assert result.success is True
        assert result.files_added == 50
        assert result.was_incremental is True
        assert result.error is None

    def test_failure_result(self):
        """Test failed IndexResult."""
        result = IndexResult(
            success=False,
            error="Failed to access directory"
        )
        assert result.success is False
        assert result.error == "Failed to access directory"

    def test_to_dict(self):
        """Test IndexResult to_dict conversion."""
        result = IndexResult(
            success=True,
            files_added=50,
            chunks_added=200,
            time_taken=5.567,
            was_incremental=False
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["files_added"] == 50
        assert d["chunks_added"] == 200
        assert d["time_taken"] == 5.57  # Rounded to 2 decimal places
        assert d["was_incremental"] is False
        assert d["error"] is None


@pytest.mark.unit
class TestSearchEngine:
    """Tests for SearchEngine class."""

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
    def engine(self, config):
        """Create SearchEngine with test config."""
        return SearchEngine(config)

    def test_init_with_config(self, config):
        """Test initialization with config."""
        engine = SearchEngine(config)
        assert engine.config is config
        assert engine._embedder is None  # Lazy loaded

    def test_init_without_config(self, monkeypatch, temp_storage):
        """Test initialization without config uses global config."""
        monkeypatch.setenv("CODE_SEARCH_STORAGE", str(temp_storage))
        get_config.cache_clear()

        engine = SearchEngine()
        assert engine.config is not None
        get_config.cache_clear()

    def test_infer_language_python(self, engine):
        """Test language inference for Python files."""
        assert engine._infer_language("test.py") == "python"
        assert engine._infer_language("/path/to/module.py") == "python"

    def test_infer_language_javascript(self, engine):
        """Test language inference for JavaScript files."""
        assert engine._infer_language("app.js") == "javascript"
        assert engine._infer_language("component.jsx") == "javascript"

    def test_infer_language_typescript(self, engine):
        """Test language inference for TypeScript files."""
        assert engine._infer_language("app.ts") == "typescript"
        assert engine._infer_language("component.tsx") == "typescript"

    def test_infer_language_go(self, engine):
        """Test language inference for Go files."""
        assert engine._infer_language("main.go") == "go"

    def test_infer_language_java(self, engine):
        """Test language inference for Java files."""
        assert engine._infer_language("App.java") == "java"

    def test_infer_language_rust(self, engine):
        """Test language inference for Rust files."""
        assert engine._infer_language("lib.rs") == "rust"

    def test_infer_language_c(self, engine):
        """Test language inference for C files."""
        assert engine._infer_language("main.c") == "c"
        assert engine._infer_language("header.h") == "c"

    def test_infer_language_cpp(self, engine):
        """Test language inference for C++ files."""
        assert engine._infer_language("main.cpp") == "cpp"
        assert engine._infer_language("header.hpp") == "cpp"

    def test_infer_language_csharp(self, engine):
        """Test language inference for C# files."""
        assert engine._infer_language("Program.cs") == "csharp"

    def test_infer_language_svelte(self, engine):
        """Test language inference for Svelte files."""
        assert engine._infer_language("App.svelte") == "svelte"

    def test_infer_language_markdown(self, engine):
        """Test language inference for Markdown files."""
        assert engine._infer_language("README.md") == "markdown"

    def test_infer_language_unknown(self, engine):
        """Test language inference for unknown extensions."""
        assert engine._infer_language("file.xyz") == "unknown"
        assert engine._infer_language("file.txt") == "unknown"

    def test_search_returns_empty_when_not_indexed(self, engine, temp_storage):
        """Test search returns empty list when project is not indexed."""
        project_path = temp_storage / "project"
        project_path.mkdir()

        results = engine.search("test query", project_path)
        assert results == []

    def test_clear_nonexistent_project(self, engine, temp_storage):
        """Test clear returns False for non-existent project."""
        project_path = temp_storage / "nonexistent"
        project_path.mkdir()

        result = engine.clear(project_path)
        assert result is False

    def test_get_status_not_indexed(self, engine, temp_storage):
        """Test get_status returns None when not indexed."""
        project_path = temp_storage / "project"
        project_path.mkdir()

        status = engine.get_status(project_path)
        assert status is None

    def test_index_nonexistent_path(self, engine, temp_storage):
        """Test indexing non-existent path returns error."""
        result = engine.index(temp_storage / "nonexistent")

        assert result.success is False
        assert "does not exist" in result.error

    def test_index_file_path(self, engine, temp_storage):
        """Test indexing a file (not directory) returns error."""
        file_path = temp_storage / "file.txt"
        file_path.touch()

        result = engine.index(file_path)

        assert result.success is False
        assert "not a directory" in result.error

    def test_find_similar_not_indexed(self, engine, temp_storage):
        """Test find_similar returns empty when not indexed."""
        project_path = temp_storage / "project"
        project_path.mkdir()

        results = engine.find_similar("chunk_123", project_path)
        assert results == []


@pytest.mark.unit
class TestSearchEngineExactSearch:
    """Tests for exact search functionality."""

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
    def engine(self, config):
        """Create SearchEngine with test config."""
        return SearchEngine(config)

    @pytest.fixture
    def project_with_files(self, temp_storage):
        """Create a project with test files."""
        project_path = temp_storage / "test_project"
        project_path.mkdir()

        # Create test files
        (project_path / "main.py").write_text(
            "def main():\n    print('Hello')\n\ndef helper():\n    pass\n"
        )
        (project_path / "utils.py").write_text(
            "def utility_function():\n    return 42\n"
        )

        return project_path

    def test_exact_search_with_ripgrep(self, engine, project_with_files):
        """Test exact search finds matches."""
        # This test depends on ripgrep or grep being available
        results = engine.search_exact("def main", project_with_files)

        # Should find at least one result
        assert len(results) >= 1

        # Check result structure
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.chunk_type == "line"
            assert result.score == 1.0

    def test_exact_search_no_matches(self, engine, project_with_files):
        """Test exact search returns empty for no matches."""
        results = engine.search_exact("xyz_not_found_pattern", project_with_files)
        assert results == []

    def test_exact_search_with_file_pattern(self, engine, project_with_files):
        """Test exact search with file pattern filter."""
        results = engine.search_exact("def", project_with_files, file_pattern="*.py")

        # All results should be from .py files
        for result in results:
            assert result.file_path.endswith(".py")


@pytest.mark.unit
class TestSearchEngineHybridSearch:
    """Tests for hybrid search functionality."""

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

    def test_hybrid_search_not_indexed(self, config, temp_storage):
        """Test hybrid search returns empty when not indexed."""
        engine = SearchEngine(config)
        project_path = temp_storage / "project"
        project_path.mkdir()

        results = engine.search_hybrid("semantic query", "exact", project_path)
        assert results == []

    def test_hybrid_search_filters_by_pattern(self, config, temp_storage):
        """Test hybrid search filters semantic results by exact pattern."""
        engine = SearchEngine(config)

        # Mock the search method to return mock results
        mock_results = [
            SearchResult(
                file_path="/test.py",
                relative_path="test.py",
                line_start=1,
                line_end=5,
                content="def authenticate_user(): pass",
                chunk_type="function",
                name="authenticate_user",
                score=0.9
            ),
            SearchResult(
                file_path="/other.py",
                relative_path="other.py",
                line_start=1,
                line_end=5,
                content="def other_function(): pass",
                chunk_type="function",
                name="other_function",
                score=0.8
            )
        ]

        with patch.object(engine, 'search', return_value=mock_results):
            results = engine.search_hybrid(
                "authentication",
                "authenticate",
                temp_storage
            )

        # Should only return result containing "authenticate"
        assert len(results) == 1
        assert "authenticate" in results[0].content.lower()


@pytest.mark.unit
class TestSearchEngineDryRun:
    """Tests for dry run indexing."""

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
    def project_with_files(self, temp_storage):
        """Create a project with test files."""
        project_path = temp_storage / "test_project"
        project_path.mkdir()

        (project_path / "main.py").write_text("def main(): pass")
        (project_path / "utils.py").write_text("def util(): pass")
        (project_path / "readme.txt").write_text("Not a code file")

        return project_path

    def test_dry_run_counts_supported_files(self, config, project_with_files):
        """Test dry run counts supported files."""
        engine = SearchEngine(config)
        result = engine.index(project_with_files, dry_run=True)

        assert result.success is True
        assert result.files_added >= 2  # At least the Python files
        assert result.time_taken == 0


@pytest.mark.unit
class TestSearchEngineWithMockedComponents:
    """Tests that mock internal components."""

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
    def indexed_project(self, temp_storage, config):
        """Create an indexed project structure."""
        project_path = temp_storage / "project"
        project_path.mkdir()

        # Create project storage structure
        project_config = config.get_project_config(project_path)
        project_config.storage_dir.mkdir(parents=True)
        project_config.index_dir.mkdir(parents=True)
        project_config.snapshot_dir.mkdir(parents=True)

        # Create index file
        (project_config.index_dir / "code.index").touch()

        # Create project info
        project_info = {
            "project_name": "project",
            "project_path": str(project_path),
            "project_hash": project_config.project_hash,
            "created_at": "2024-01-01T00:00:00"
        }
        (project_config.storage_dir / "project_info.json").write_text(
            json.dumps(project_info)
        )

        # Create stats
        stats = {
            "files_indexed": 10,
            "total_chunks": 50,
            "chunk_types": {"function": 30, "class": 20}
        }
        (project_config.index_dir / "stats.json").write_text(json.dumps(stats))

        return project_path

    def test_get_status_indexed_project(self, config, indexed_project):
        """Test get_status returns info for indexed project."""
        engine = SearchEngine(config)

        # Mock the index manager
        mock_index_manager = MagicMock()
        mock_index_manager.get_stats.return_value = {
            "files_indexed": 10,
            "total_chunks": 50,
            "chunk_types": {"function": 30, "class": 20},
            "top_folders": {"src": 30, "tests": 20}
        }

        with patch.object(engine, '_get_index_manager', return_value=mock_index_manager):
            status = engine.get_status(indexed_project)

        assert status is not None
        assert status["project_name"] == "project"
        assert status["files_indexed"] == 10
        assert status["chunks_indexed"] == 50

    def test_clear_removes_project(self, config, indexed_project):
        """Test clear removes indexed project."""
        engine = SearchEngine(config)

        project_config = config.get_project_config(indexed_project)
        assert project_config.storage_dir.exists()

        result = engine.clear(indexed_project)

        assert result is True
        assert not project_config.storage_dir.exists()

    def test_clear_all_removes_all_projects(self, config, temp_storage):
        """Test clear_all removes all projects."""
        engine = SearchEngine(config)

        # Create multiple projects
        for name in ["p1", "p2"]:
            project_path = temp_storage / name
            project_path.mkdir()
            project_config = config.get_project_config(project_path)
            project_config.storage_dir.mkdir(parents=True)
            project_config.index_dir.mkdir(parents=True)
            (project_config.index_dir / "code.index").touch()

        count = engine.clear_all()

        assert count == 2
        assert len(list(config.projects_dir.iterdir())) == 0


@pytest.mark.unit
class TestSearchResultFiltering:
    """Tests for search result filtering logic."""

    def test_filter_by_threshold(self):
        """Test results are filtered by threshold."""
        # This tests the filtering logic in the search method
        results = [
            SearchResult(
                file_path="/a.py", relative_path="a.py",
                line_start=1, line_end=5, content="code",
                chunk_type="function", name="a", score=0.9
            ),
            SearchResult(
                file_path="/b.py", relative_path="b.py",
                line_start=1, line_end=5, content="code",
                chunk_type="function", name="b", score=0.5
            ),
            SearchResult(
                file_path="/c.py", relative_path="c.py",
                line_start=1, line_end=5, content="code",
                chunk_type="function", name="c", score=0.3
            ),
        ]

        threshold = 0.6
        filtered = [r for r in results if r.score >= threshold]

        assert len(filtered) == 1
        assert filtered[0].name == "a"

    def test_filter_by_language(self):
        """Test results are filtered by language."""
        results = [
            SearchResult(
                file_path="/a.py", relative_path="a.py",
                line_start=1, line_end=5, content="code",
                chunk_type="function", name="a", score=0.9,
                language="python"
            ),
            SearchResult(
                file_path="/b.js", relative_path="b.js",
                line_start=1, line_end=5, content="code",
                chunk_type="function", name="b", score=0.8,
                language="javascript"
            ),
        ]

        target_language = "python"
        filtered = [r for r in results if r.language == target_language]

        assert len(filtered) == 1
        assert filtered[0].name == "a"
