"""MCP command for csearch CLI - start MCP server."""

import sys
from pathlib import Path

import click

from cli.output.colors import ColoredOutput


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport protocol (stdio for Claude Code, sse for HTTP)."
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for SSE transport (default: 8000)."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def mcp(
    ctx: click.Context,
    transport: str,
    port: int,
    no_color: bool,
) -> None:
    """Start the MCP server for Claude Code integration.

    The MCP server exposes semantic search capabilities to AI assistants
    like Claude Code via the Model Context Protocol.

    \b
    Examples:
      csearch mcp                       Start MCP server (stdio transport)
      csearch mcp --transport sse       Start with HTTP/SSE transport
      csearch mcp --port 9000           Use custom port for SSE

    \b
    To add to Claude Code:
      claude mcp add code-search -- csearch mcp
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    try:
        # Import and run the MCP server
        from mcp_server.server import main as run_mcp_server

        if transport == "stdio":
            # For stdio, just run silently
            run_mcp_server()
        else:
            click.echo(colors.info(f"Starting MCP server on port {port}..."))
            click.echo(f"Transport: {transport}")
            click.echo("Press Ctrl+C to stop.\n")
            run_mcp_server()

    except ImportError as e:
        click.echo(colors.error(f"Failed to import MCP server: {e}"), err=True)
        click.echo("Make sure fastmcp is installed: pip install fastmcp")
        sys.exit(1)
    except Exception as e:
        click.echo(colors.error(f"MCP server error: {e}"), err=True)
        sys.exit(1)
