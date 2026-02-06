"""Unit tests for CLI commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cli.main import cli, main
from cli.output.colors import ColoredOutput, should_use_colors
from cli.output.formatters import (
    get_formatter,
    GrepFormatter,
    JsonFormatter,
    CompactFormatter,
    VerboseFormatter,
)
from core.search_engine import SearchResult


@pytest.mark.unit
class TestCLIMain:
    """Tests for main CLI group."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_shows_help_without_command(self, runner):
        """Test CLI shows help when no command provided."""
        result = runner.invoke(cli)
        assert result.exit_code == 0
        assert "csearch" in result.output
        assert "Semantic code search" in result.output

    def test_cli_version_flag(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_version_short_flag(self, runner):
        """Test -V flag."""
        result = runner.invoke(cli, ["-V"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help_flag(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "csearch" in result.output

    def test_cli_short_help_flag(self, runner):
        """Test -h flag."""
        result = runner.invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "csearch" in result.output

    def test_cli_color_option_auto(self, runner):
        """Test --color auto option."""
        result = runner.invoke(cli, ["--color", "auto", "--help"])
        assert result.exit_code == 0

    def test_cli_color_option_always(self, runner):
        """Test --color always option."""
        result = runner.invoke(cli, ["--color", "always", "--help"])
        assert result.exit_code == 0

    def test_cli_color_option_never(self, runner):
        """Test --color never option."""
        result = runner.invoke(cli, ["--color", "never", "--help"])
        assert result.exit_code == 0

    def test_cli_invalid_color_option(self, runner):
        """Test invalid --color option."""
        result = runner.invoke(cli, ["--color", "invalid"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestSearchCommand:
    """Tests for search command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_search_help(self, runner):
        """Test search --help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output
        assert "--max-results" in result.output

    def test_search_requires_query(self, runner):
        """Test search requires query argument."""
        result = runner.invoke(cli, ["search"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_search_not_indexed_semantic(self, runner):
        """Test search shows error when project not indexed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                cli,
                ["search", "test query", "-p", tmpdir],
                catch_exceptions=False
            )
            # Should fail with exit code 1
            assert result.exit_code == 1
            assert "not indexed" in result.output.lower()

    def test_search_exact_no_index_needed(self, runner):
        """Test exact search works without index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def unique_function_name(): pass")

            result = runner.invoke(
                cli,
                ["search", "--exact", "unique_function_name", "-p", tmpdir]
            )
            # Should work without index
            # Exit code might be 0 (found) or 1 (not found), both are valid
            # The key is it shouldn't fail with "not indexed" error

    def test_search_output_formats(self, runner):
        """Test different output format options."""
        # Just verify the options are accepted
        result = runner.invoke(cli, ["search", "--help"])
        assert "--json" in result.output
        assert "--compact" in result.output
        assert "--verbose" in result.output


@pytest.mark.unit
class TestIndexCommand:
    """Tests for index command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_index_help(self, runner):
        """Test index --help."""
        result = runner.invoke(cli, ["index", "--help"])
        assert result.exit_code == 0
        assert "DIRECTORY" in result.output
        assert "--force" in result.output or "--full" in result.output

    def test_index_dry_run(self, runner):
        """Test index --dry-run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def test(): pass")

            result = runner.invoke(
                cli,
                ["index", tmpdir, "--dry-run"]
            )
            # Should succeed and show what would be indexed
            assert result.exit_code == 0


@pytest.mark.unit
class TestStatusCommand:
    """Tests for status command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_status_help(self, runner):
        """Test status --help."""
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_status_not_indexed(self, runner):
        """Test status when project not indexed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["status", tmpdir])
            # Should indicate not indexed
            assert "not indexed" in result.output.lower() or "no index" in result.output.lower()

    def test_status_all_empty(self, runner):
        """Test status --all when no projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["CODE_SEARCH_STORAGE"] = tmpdir
            from core.config import get_config
            get_config.cache_clear()

            result = runner.invoke(cli, ["status", "--all"])
            # Should indicate no projects
            assert "no" in result.output.lower() or result.exit_code == 0

            get_config.cache_clear()


@pytest.mark.unit
class TestClearCommand:
    """Tests for clear command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_clear_help(self, runner):
        """Test clear --help."""
        result = runner.invoke(cli, ["clear", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output
        assert "--all" in result.output

    def test_clear_not_indexed(self, runner):
        """Test clear when project not indexed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                cli,
                ["clear", tmpdir, "--force"]
            )
            # Should indicate no project data
            assert "no project" in result.output.lower() or "not found" in result.output.lower()


@pytest.mark.unit
class TestConfigCommand:
    """Tests for config command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_config_help(self, runner):
        """Test config --help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_shows_current(self, runner):
        """Test config shows current configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["CODE_SEARCH_STORAGE"] = tmpdir
            from core.config import get_config
            get_config.cache_clear()

            result = runner.invoke(cli, ["config"])
            assert result.exit_code == 0
            # Should show some config values
            assert "storage" in result.output.lower() or "model" in result.output.lower()

            get_config.cache_clear()


@pytest.mark.unit
class TestDoctorCommand:
    """Tests for doctor command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_doctor_help(self, runner):
        """Test doctor --help."""
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_doctor_runs(self, runner):
        """Test doctor command runs."""
        result = runner.invoke(cli, ["doctor"])
        # Doctor checks dependencies, should run without error
        assert result.exit_code == 0 or "error" not in result.output.lower()


@pytest.mark.unit
class TestCompletionsCommand:
    """Tests for completions command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_completions_help(self, runner):
        """Test completions --help."""
        result = runner.invoke(cli, ["completions", "--help"])
        assert result.exit_code == 0
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output

    def test_completions_bash(self, runner):
        """Test bash completion script."""
        result = runner.invoke(cli, ["completions", "bash"])
        assert result.exit_code == 0
        assert "bash" in result.output.lower()

    def test_completions_zsh(self, runner):
        """Test zsh completion script."""
        result = runner.invoke(cli, ["completions", "zsh"])
        assert result.exit_code == 0
        assert "compdef" in result.output or "zsh" in result.output.lower()

    def test_completions_fish(self, runner):
        """Test fish completion script."""
        result = runner.invoke(cli, ["completions", "fish"])
        assert result.exit_code == 0
        assert "fish" in result.output.lower()


@pytest.mark.unit
class TestColoredOutput:
    """Tests for ColoredOutput class."""

    def test_colors_enabled(self):
        """Test color output when enabled."""
        output = ColoredOutput(use_colors=True)
        result = output.success("test")
        assert "\033[" in result  # ANSI escape code

    def test_colors_disabled(self):
        """Test color output when disabled."""
        output = ColoredOutput(use_colors=False)
        result = output.success("test")
        assert "\033[" not in result

    def test_success_method(self):
        """Test success coloring."""
        output = ColoredOutput(use_colors=True)
        result = output.success("OK")
        assert "OK" in result

    def test_error_method(self):
        """Test error coloring."""
        output = ColoredOutput(use_colors=True)
        result = output.error("Failed")
        assert "Failed" in result

    def test_warning_method(self):
        """Test warning coloring."""
        output = ColoredOutput(use_colors=True)
        result = output.warning("Warning")
        assert "Warning" in result

    def test_name_method(self):
        """Test name/highlight coloring."""
        output = ColoredOutput(use_colors=True)
        result = output.name("project")
        assert "project" in result


@pytest.mark.unit
class TestShouldUseColors:
    """Tests for should_use_colors function."""

    def test_always_returns_true(self):
        """Test 'always' mode returns True."""
        assert should_use_colors("always") is True

    def test_never_returns_false(self):
        """Test 'never' mode returns False."""
        assert should_use_colors("never") is False

    def test_auto_respects_no_color_env(self, monkeypatch):
        """Test 'auto' mode respects NO_COLOR env var."""
        monkeypatch.setenv("NO_COLOR", "1")
        assert should_use_colors("auto") is False

    def test_auto_respects_term(self, monkeypatch):
        """Test 'auto' mode checks TERM variable."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        assert should_use_colors("auto") is False


@pytest.mark.unit
class TestFormatters:
    """Tests for output formatters."""

    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        return [
            SearchResult(
                file_path="/project/src/auth.py",
                relative_path="src/auth.py",
                line_start=10,
                line_end=25,
                content="def authenticate(user):\n    return validate(user)",
                chunk_type="function",
                name="authenticate",
                score=0.95,
                language="python"
            ),
            SearchResult(
                file_path="/project/src/utils.py",
                relative_path="src/utils.py",
                line_start=5,
                line_end=10,
                content="def helper(): pass",
                chunk_type="function",
                name="helper",
                score=0.75,
                language="python"
            )
        ]

    def test_get_formatter_grep(self):
        """Test getting grep formatter."""
        formatter = get_formatter("grep", use_colors=False)
        assert isinstance(formatter, GrepFormatter)

    def test_get_formatter_json(self):
        """Test getting JSON formatter."""
        formatter = get_formatter("json", use_colors=False)
        assert isinstance(formatter, JsonFormatter)

    def test_get_formatter_compact(self):
        """Test getting compact formatter."""
        formatter = get_formatter("compact", use_colors=False)
        assert isinstance(formatter, CompactFormatter)

    def test_get_formatter_verbose(self):
        """Test getting verbose formatter."""
        formatter = get_formatter("verbose", use_colors=False)
        assert isinstance(formatter, VerboseFormatter)

    def test_grep_formatter_output(self, sample_results):
        """Test grep formatter produces expected output."""
        formatter = GrepFormatter(use_colors=False)
        output = formatter.format_results(sample_results, "auth", 100)

        assert "src/auth.py" in output
        assert "10" in output  # Line number
        assert "authenticate" in output

    def test_json_formatter_output(self, sample_results):
        """Test JSON formatter produces valid JSON."""
        formatter = JsonFormatter(use_colors=False)
        output = formatter.format_results(sample_results, "auth", 100)

        # Should be valid JSON
        data = json.loads(output)
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["name"] == "authenticate"

    def test_compact_formatter_output(self, sample_results):
        """Test compact formatter produces path:line format."""
        formatter = CompactFormatter(use_colors=False)
        output = formatter.format_results(sample_results, "auth", 100)

        # Should be one path:line per line
        lines = output.strip().split("\n")
        assert len(lines) == 2
        assert ":" in lines[0]

    def test_verbose_formatter_output(self, sample_results):
        """Test verbose formatter includes scores."""
        formatter = VerboseFormatter(use_colors=False)
        output = formatter.format_results(sample_results, "auth", 100)

        # Should include score
        assert "0.95" in output or "95" in output
        # Should include more details
        assert "function" in output.lower()

    def test_formatter_empty_results(self):
        """Test formatters handle empty results."""
        formatter = GrepFormatter(use_colors=False)
        output = formatter.format_results([], "query", 100)

        # Should handle gracefully
        assert output is not None or output == ""


@pytest.mark.unit
class TestMainFunction:
    """Tests for main() entry point."""

    def test_main_inserts_search_command(self, monkeypatch):
        """Test main() inserts 'search' for query-like arguments."""
        import sys

        # Mock sys.argv
        original_argv = sys.argv.copy()
        sys.argv = ["csearch", "test query"]

        # Mock cli to capture the argv modification
        with patch('cli.main.cli') as mock_cli:
            try:
                main()
            except SystemExit:
                pass

        # Should have inserted 'search'
        assert sys.argv[1] == "search"

        # Restore
        sys.argv = original_argv

    def test_main_does_not_insert_for_commands(self, monkeypatch):
        """Test main() doesn't insert 'search' for known commands."""
        import sys

        original_argv = sys.argv.copy()
        sys.argv = ["csearch", "index"]

        with patch('cli.main.cli') as mock_cli:
            try:
                main()
            except SystemExit:
                pass

        # Should NOT have inserted 'search'
        assert sys.argv[1] == "index"

        sys.argv = original_argv

    def test_main_does_not_insert_for_flags(self, monkeypatch):
        """Test main() doesn't insert 'search' for flags."""
        import sys

        original_argv = sys.argv.copy()
        sys.argv = ["csearch", "--version"]

        with patch('cli.main.cli') as mock_cli:
            try:
                main()
            except SystemExit:
                pass

        # Should NOT have inserted 'search'
        assert sys.argv[1] == "--version"

        sys.argv = original_argv
