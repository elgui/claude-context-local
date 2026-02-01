"""Main entry point for csearch CLI."""

import sys
from pathlib import Path

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.output.colors import should_use_colors


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option(
    "--version", "-V",
    is_flag=True,
    help="Show version and exit."
)
@click.option(
    "--color",
    type=click.Choice(["auto", "always", "never"]),
    default="auto",
    help="When to use colors in output."
)
@click.pass_context
def cli(ctx: click.Context, version: bool, color: str) -> None:
    """csearch - Semantic code search for your codebase.

    A grep-like CLI tool for semantic code search that runs 100% locally.

    \b
    Examples:
      csearch "authentication handling"     Search for auth-related code
      csearch -m 10 "database connection"   Get up to 10 results
      csearch -f "*.py" "async function"    Search only Python files
      csearch --json "error handling"       Output as JSON
      csearch index                         Index current directory
      csearch status                        Show index information

    \b
    For more information:
      csearch <command> --help              Show help for a specific command
    """
    ctx.ensure_object(dict)
    ctx.obj["color"] = color
    ctx.obj["use_colors"] = should_use_colors(color)

    if version:
        click.echo("csearch version 0.1.0")
        ctx.exit(0)

    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Import and register commands
from cli.commands.search import search
from cli.commands.index import index
from cli.commands.status import status
from cli.commands.watch import watch
from cli.commands.config import config
from cli.commands.clear import clear
from cli.commands.mcp import mcp
from cli.commands.doctor import doctor

cli.add_command(search)
cli.add_command(index)
cli.add_command(status)
cli.add_command(watch)
cli.add_command(config)
cli.add_command(clear)
cli.add_command(mcp)
cli.add_command(doctor)


# Shell completions command
@cli.command(name="completions")
@click.argument(
    "shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    required=False,
)
@click.option(
    "--install",
    is_flag=True,
    help="Install completions to the appropriate location."
)
@click.pass_context
def completions_cmd(ctx: click.Context, shell: str, install: bool) -> None:
    """Generate or install shell completions.

    \b
    Examples:
      csearch completions bash              Show bash completion script
      csearch completions zsh --install     Install zsh completions
      csearch completions fish --install    Install fish completions
    """
    from cli.completions import (
        detect_shell,
        get_completion_script,
        install_completion,
        get_completion_install_path,
    )
    from cli.output.colors import ColoredOutput

    use_colors = ctx.obj.get("use_colors", True)
    colors = ColoredOutput(use_colors)

    if shell is None:
        shell = detect_shell()
        click.echo(f"Detected shell: {shell}")

    if install:
        path = get_completion_install_path(shell)
        if install_completion(shell):
            click.echo(colors.success(f"Installed completions to: {path}"))
            click.echo()
            if shell == "bash":
                click.echo("Add to your ~/.bashrc:")
                click.echo(f"  source {path}")
            elif shell == "zsh":
                click.echo("Add to your ~/.zshrc (before compinit):")
                click.echo(f"  fpath=(~/.zfunc $fpath)")
            elif shell == "fish":
                click.echo("Completions will be loaded automatically.")
        else:
            click.echo(colors.error("Failed to install completions."))
    else:
        script = get_completion_script(shell)
        if script:
            click.echo(script)
        else:
            click.echo(colors.error(f"Unknown shell: {shell}"))


# Also allow search as the default command when query is provided
@cli.command(name="query", hidden=True)
@click.argument("query")
@click.pass_context
def default_search(ctx: click.Context, query: str) -> None:
    """Hidden command for default search behavior."""
    ctx.invoke(search, query=query)


def main() -> None:
    """Main entry point."""
    # Check if first argument looks like a query (not a command or flag)
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # If first arg doesn't look like a command or flag, treat as search query
        commands = ["search", "index", "status", "watch", "config", "clear", "mcp", "doctor", "completions", "version"]
        if not first_arg.startswith("-") and first_arg not in commands:
            # Insert "search" command
            sys.argv.insert(1, "search")

    cli()


if __name__ == "__main__":
    main()
