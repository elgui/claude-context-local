"""Clear command for csearch CLI."""

import sys
from pathlib import Path

import click

from core.search_engine import SearchEngine
from core.project import ProjectManager
from cli.output.colors import ColoredOutput


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--all", "-a",
    "clear_all",
    is_flag=True,
    help="Clear all indexed projects."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Skip confirmation prompt."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def clear(
    ctx: click.Context,
    directory: Path,
    clear_all: bool,
    force: bool,
    no_color: bool,
) -> None:
    """Clear index for a project.

    DIRECTORY is the path to clear. Defaults to current directory.

    \b
    Examples:
      csearch clear                     Clear index for current directory
      csearch clear /path/to/project    Clear index for specific project
      csearch clear --all               Clear all indexed projects
      csearch clear --force             Skip confirmation prompt
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    engine = SearchEngine()

    if clear_all:
        # Clear all projects
        projects = ProjectManager().list_projects()
        count = len(projects)

        if count == 0:
            click.echo("No indexed projects found.")
            return

        if not force:
            click.echo(colors.warning(f"This will delete indexes for {count} project(s)."))
            if not click.confirm("Are you sure?"):
                click.echo("Aborted.")
                return

        removed = engine.clear_all()
        click.echo(colors.success(f"Cleared {removed} project(s)."))
        return

    # Clear specific project
    directory = (directory or Path.cwd()).resolve()

    # Get project config to check if any project data exists
    project_manager = ProjectManager()
    project_config = project_manager.get_project_config(directory)

    # Check if any project data exists (even partial)
    has_project_data = project_config.storage_dir.exists()
    status = engine.get_status(directory)

    if not has_project_data:
        click.echo(colors.warning(f"No project data found for: {directory}"))
        return

    if not force:
        if status:
            name = status.get("project_name", directory.name)
            files = status.get("files_indexed", 0)
            chunks = status.get("chunks_indexed", 0)
            click.echo(f"Project: {colors.name(name)}")
            click.echo(f"Files: {files}, Chunks: {chunks}")
        else:
            click.echo(f"Project: {colors.name(directory.name)}")
            click.echo(colors.warning("(partially indexed or corrupted)"))
        click.echo()

        if not click.confirm(colors.warning("Delete this project data?")):
            click.echo("Aborted.")
            return

    if engine.clear(directory):
        click.echo(colors.success("Project data cleared."))
    else:
        click.echo(colors.error("Failed to clear project data."), err=True)
        sys.exit(1)
