"""Terminal color utilities for csearch CLI."""

import os
import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    # Reset
    RESET = "\033[0m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Semantic colors for csearch
    FILE_PATH = CYAN
    LINE_NUMBER = GREEN
    MATCH = BOLD
    SCORE = YELLOW
    CHUNK_TYPE = MAGENTA
    NAME = BRIGHT_WHITE
    SEPARATOR = DIM
    ERROR = RED
    SUCCESS = GREEN
    WARNING = YELLOW
    INFO = BLUE


def should_use_colors(color_setting: str = "auto") -> bool:
    """Determine whether to use colors in output.

    Args:
        color_setting: One of "auto", "always", or "never".

    Returns:
        True if colors should be used.
    """
    # Honor NO_COLOR environment variable (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False

    # Honor FORCE_COLOR environment variable
    if os.environ.get("FORCE_COLOR"):
        return True

    if color_setting == "never":
        return False
    elif color_setting == "always":
        return True
    else:  # auto
        # Check if stdout is a TTY
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class ColoredOutput:
    """Context manager for colored output."""

    def __init__(self, use_colors: bool = True):
        """Initialize colored output.

        Args:
            use_colors: Whether to use colors.
        """
        self.use_colors = use_colors

    def colorize(self, text: str, *codes: str) -> str:
        """Apply color codes to text.

        Args:
            text: Text to colorize.
            *codes: Color codes to apply.

        Returns:
            Colorized text if colors are enabled.
        """
        if not self.use_colors:
            return text
        return "".join(codes) + text + Colors.RESET

    def file_path(self, path: str) -> str:
        """Format a file path."""
        return self.colorize(path, Colors.FILE_PATH)

    def line_number(self, line: int) -> str:
        """Format a line number."""
        return self.colorize(str(line), Colors.LINE_NUMBER)

    def match(self, text: str) -> str:
        """Format matched text."""
        return self.colorize(text, Colors.MATCH)

    def score(self, value: float) -> str:
        """Format a score value."""
        return self.colorize(f"{value:.3f}", Colors.SCORE)

    def chunk_type(self, ctype: str) -> str:
        """Format a chunk type."""
        return self.colorize(ctype, Colors.CHUNK_TYPE)

    def name(self, text: str) -> str:
        """Format a name."""
        return self.colorize(text, Colors.NAME)

    def separator(self, text: str = "--") -> str:
        """Format a separator."""
        return self.colorize(text, Colors.SEPARATOR)

    def error(self, text: str) -> str:
        """Format error text."""
        return self.colorize(text, Colors.ERROR)

    def success(self, text: str) -> str:
        """Format success text."""
        return self.colorize(text, Colors.SUCCESS)

    def warning(self, text: str) -> str:
        """Format warning text."""
        return self.colorize(text, Colors.WARNING)

    def info(self, text: str) -> str:
        """Format info text."""
        return self.colorize(text, Colors.INFO)

    def dim(self, text: str) -> str:
        """Format dimmed text."""
        return self.colorize(text, Colors.DIM)
