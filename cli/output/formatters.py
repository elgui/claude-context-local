"""Output formatters for csearch CLI."""

import json
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, TextIO

from core.search_engine import SearchResult
from cli.output.colors import ColoredOutput, should_use_colors


class OutputFormatter(ABC):
    """Base class for output formatters."""

    def __init__(
        self,
        use_colors: bool = True,
        context_lines: int = 0,
        truncate_lines: int = 120,
        output: TextIO = None,
    ):
        """Initialize formatter.

        Args:
            use_colors: Whether to use colors.
            context_lines: Number of context lines to show.
            truncate_lines: Maximum line length before truncation.
            output: Output stream (defaults to stdout).
        """
        self.colors = ColoredOutput(use_colors)
        self.context_lines = context_lines
        self.truncate_lines = truncate_lines
        self.output = output or sys.stdout

    @abstractmethod
    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format search results.

        Args:
            results: List of search results.
            query: Original search query.
            elapsed_ms: Time taken in milliseconds.

        Returns:
            Formatted output string.
        """
        pass

    def write(self, text: str) -> None:
        """Write text to output stream."""
        self.output.write(text)
        if not text.endswith("\n"):
            self.output.write("\n")

    def truncate(self, text: str) -> str:
        """Truncate text to maximum line length."""
        if self.truncate_lines <= 0:
            return text
        if len(text) > self.truncate_lines:
            return text[: self.truncate_lines - 3] + "..."
        return text


class GrepFormatter(OutputFormatter):
    """Grep-style output formatter."""

    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format results in grep-style output.

        Format: file:line: content
        """
        if not results:
            return ""

        lines = []
        prev_file = None

        for result in results:
            # Add separator between non-contiguous results
            if prev_file is not None and prev_file != result.relative_path:
                lines.append(self.colors.separator("--"))

            # Format: file:line: content
            file_part = self.colors.file_path(result.relative_path)
            line_part = self.colors.line_number(result.line_start)

            # Get first non-empty line of content
            content = self._get_content_preview(result.content)
            content = self.truncate(content)

            line = f"{file_part}:{line_part}: {content}"
            lines.append(line)

            # Add context lines if requested
            if self.context_lines > 0:
                context = self._format_context(result)
                if context:
                    lines.extend(context)

            prev_file = result.relative_path

        return "\n".join(lines)

    def _get_content_preview(self, content: str) -> str:
        """Get a preview of content (first non-empty line)."""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _format_context(self, result: SearchResult) -> List[str]:
        """Format context lines for a result."""
        lines = []
        content_lines = result.content.split("\n")

        for i, line in enumerate(content_lines[1 : self.context_lines + 1], 1):
            line_num = result.line_start + i
            line_part = self.colors.dim(f"{line_num}")
            content = self.truncate(line.rstrip())
            lines.append(f"  {line_part}: {content}")

        return lines


class JsonFormatter(OutputFormatter):
    """JSON output formatter."""

    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format results as JSON."""
        output = {
            "query": query,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
        if elapsed_ms is not None:
            output["elapsed_ms"] = round(elapsed_ms, 2)

        return json.dumps(output, indent=2)


class CompactFormatter(OutputFormatter):
    """Compact output formatter (one result per line, path:line only)."""

    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format results as compact path:line output."""
        lines = []
        for result in results:
            line = f"{result.relative_path}:{result.line_start}"
            lines.append(self.colors.file_path(line) if self.colors.use_colors else line)
        return "\n".join(lines)


class VerboseFormatter(OutputFormatter):
    """Verbose output formatter with scores and metadata."""

    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format results with full metadata."""
        if not results:
            return "No results found."

        lines = []

        # Header
        header = f'Results for "{query}"'
        if elapsed_ms is not None:
            header += f" ({elapsed_ms:.0f}ms)"
        lines.append(self.colors.info(header))
        lines.append("")

        for i, result in enumerate(results, 1):
            # Score and location
            score = self.colors.score(result.score)
            file_path = self.colors.file_path(result.relative_path)
            line_range = f"{result.line_start}-{result.line_end}"
            line_range = self.colors.line_number(line_range)

            # Chunk info
            chunk_type = self.colors.chunk_type(result.chunk_type)
            name_info = ""
            if result.name:
                name_info = f": {self.colors.name(result.name)}"

            lines.append(f"[{score}] {file_path}:{line_range} ({chunk_type}{name_info})")

            # Content preview (indented)
            content_lines = result.content.split("\n")
            for j, content_line in enumerate(content_lines[:5]):  # Max 5 lines
                content = self.truncate(content_line.rstrip())
                if j == 0:
                    lines.append(f"        {content}")
                else:
                    lines.append(f"        {self.colors.dim(content)}")

            if len(content_lines) > 5:
                lines.append(self.colors.dim(f"        ... ({len(content_lines) - 5} more lines)"))

            lines.append("")

        return "\n".join(lines)


class TableFormatter(OutputFormatter):
    """Table output formatter for status and list commands."""

    def format_results(
        self,
        results: List[SearchResult],
        query: str,
        elapsed_ms: Optional[float] = None,
    ) -> str:
        """Format results as a table."""
        if not results:
            return "No results found."

        # Calculate column widths
        max_path = max(len(r.relative_path) for r in results)
        max_path = min(max_path, 50)  # Cap at 50 chars

        lines = []

        # Header
        header = f"{'File':<{max_path}} {'Lines':<12} {'Type':<12} {'Score':<8} {'Name'}"
        lines.append(self.colors.dim(header))
        lines.append(self.colors.dim("-" * len(header)))

        for result in results:
            path = result.relative_path[:max_path]
            line_range = f"{result.line_start}-{result.line_end}"
            name = result.name or ""

            line = f"{path:<{max_path}} {line_range:<12} {result.chunk_type:<12} {result.score:<8.3f} {name}"
            lines.append(line)

        return "\n".join(lines)


def get_formatter(
    format_type: str,
    use_colors: bool = True,
    context_lines: int = 0,
    truncate_lines: int = 120,
    output: TextIO = None,
) -> OutputFormatter:
    """Get an output formatter by type.

    Args:
        format_type: One of "grep", "json", "compact", "verbose", "table".
        use_colors: Whether to use colors.
        context_lines: Number of context lines.
        truncate_lines: Maximum line length.
        output: Output stream.

    Returns:
        OutputFormatter instance.
    """
    formatters = {
        "grep": GrepFormatter,
        "json": JsonFormatter,
        "compact": CompactFormatter,
        "verbose": VerboseFormatter,
        "table": TableFormatter,
    }

    formatter_class = formatters.get(format_type, GrepFormatter)
    return formatter_class(
        use_colors=use_colors,
        context_lines=context_lines,
        truncate_lines=truncate_lines,
        output=output,
    )
