"""CLI commands for csearch."""

from cli.commands.search import search
from cli.commands.index import index
from cli.commands.status import status
from cli.commands.watch import watch
from cli.commands.config import config
from cli.commands.clear import clear
from cli.commands.mcp import mcp
from cli.commands.doctor import doctor

__all__ = [
    "search",
    "index",
    "status",
    "watch",
    "config",
    "clear",
    "mcp",
    "doctor",
]
