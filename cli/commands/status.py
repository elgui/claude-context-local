"""Status command for csearch CLI."""

import sys
from pathlib import Path
from datetime import datetime

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
    "show_all",
    is_flag=True,
    help="List all indexed projects."
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def status(
    ctx: click.Context,
    directory: Path,
    show_all: bool,
    output_json: bool,
    no_color: bool,
) -> None:
    """Show index status for a project.

    DIRECTORY is the path to check. Defaults to current directory.

    \b
    Examples:
      csearch status                    Show status for current directory
      csearch status /path/to/project   Show status for specific project
      csearch status --all              List all indexed projects
      csearch status --json             Output as JSON
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    engine = SearchEngine()

    if show_all:
        # List all indexed projects
        projects = ProjectManager().list_projects()

        if output_json:
            import json
            data = {
                "projects": [p.to_dict() for p in projects],
                "count": len(projects),
            }
            click.echo(json.dumps(data, indent=2))
            return

        if not projects:
            click.echo("No indexed projects found.")
            return

        click.echo(colors.info(f"Indexed projects ({len(projects)}):"))
        click.echo()

        for project in projects:
            path = project.project_path
            name = project.project_name
            files = project.files_indexed or 0
            chunks = project.chunks_indexed or 0

            # Format status indicators
            status_tags = []
            if project.watcher_running:
                status_tags.append(colors.success("[watching]"))
            if not project.is_fully_indexed:
                status_tags.append(colors.warning("[incomplete]"))

            status_str = " ".join(status_tags)
            if status_str:
                status_str = " " + status_str

            click.echo(f"  {colors.name(name)}{status_str}")
            click.echo(f"    Path: {colors.file_path(path)}")
            click.echo(f"    Files: {files}, Chunks: {chunks}")
            if project.last_indexed:
                click.echo(f"    Last indexed: {project.last_indexed}")
            click.echo()

        return

    # Show status for specific project
    directory = (directory or Path.cwd()).resolve()

    status_info = engine.get_status(directory)

    if output_json:
        import json
        if status_info:
            click.echo(json.dumps(status_info, indent=2))
        else:
            click.echo(json.dumps({"error": "Project not indexed", "path": str(directory)}))
            sys.exit(1)
        return

    if status_info is None:
        click.echo(colors.warning(f"Project not indexed: {directory}"))
        click.echo(f"\nRun '{colors.info('csearch index')}' to index this project.")
        sys.exit(1)

    # Display status
    click.echo(colors.info("Project Status"))
    click.echo()
    click.echo(f"  Project: {colors.name(status_info.get('project_name', 'unknown'))}")
    click.echo(f"  Path: {colors.file_path(status_info.get('project_path', str(directory)))}")
    click.echo()

    # Index info
    click.echo(colors.info("Index Information"))
    click.echo(f"  Files indexed: {status_info.get('files_indexed', 0)}")
    click.echo(f"  Total chunks: {status_info.get('chunks_indexed', 0)}")
    click.echo(f"  Index size: {status_info.get('index_size_mb', 0):.2f} MB")
    click.echo()

    # Chunk types
    chunk_types = status_info.get("chunk_types", {})
    if chunk_types:
        click.echo(colors.info("Chunk Types"))
        for ctype, count in sorted(chunk_types.items(), key=lambda x: -x[1]):
            click.echo(f"  {ctype}: {count}")
        click.echo()

    # Top folders
    top_folders = status_info.get("top_folders", {})
    if top_folders:
        click.echo(colors.info("Top Folders"))
        for folder, count in list(sorted(top_folders.items(), key=lambda x: -x[1]))[:5]:
            click.echo(f"  {folder}: {count} chunks")
        click.echo()

    # Watcher status
    if status_info.get("watcher_running"):
        pid = status_info.get("watcher_pid")
        click.echo(colors.success(f"Watcher: running (pid {pid})"))
    else:
        click.echo(colors.dim("Watcher: not running"))

    # Last indexed
    if last_indexed := status_info.get("last_indexed"):
        click.echo(f"Last indexed: {last_indexed}")
