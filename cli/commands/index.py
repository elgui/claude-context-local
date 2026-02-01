"""Index command for csearch CLI."""

import sys
from pathlib import Path

import click

from core.search_engine import SearchEngine
from cli.output.colors import ColoredOutput, should_use_colors


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option(
    "--full",
    is_flag=True,
    help="Force full re-index (ignore incremental updates)."
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be indexed without actually indexing."
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show index statistics after indexing."
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Show verbose progress information."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def index(
    ctx: click.Context,
    directory: Path,
    full: bool,
    dry_run: bool,
    stats: bool,
    verbose: bool,
    no_color: bool,
) -> None:
    """Index a directory for semantic search.

    DIRECTORY is the path to index. Defaults to current directory.

    \b
    Examples:
      csearch index                     Index current directory
      csearch index /path/to/project    Index a specific directory
      csearch index --full              Force full re-index
      csearch index --dry-run           Show what would be indexed
      csearch index --stats             Show statistics after indexing
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    directory = directory.resolve()

    if verbose:
        click.echo(f"Indexing: {colors.file_path(str(directory))}")
        if full:
            click.echo("Mode: Full re-index")
        else:
            click.echo("Mode: Incremental (only changed files)")
        if dry_run:
            click.echo(colors.warning("Dry run - no changes will be made"))

    # Initialize search engine
    engine = SearchEngine()

    # Perform indexing
    result = engine.index(
        project_path=directory,
        force_full=full,
        dry_run=dry_run,
    )

    # Report results
    if result.success:
        if dry_run:
            click.echo(f"\n{colors.info('Dry run results:')}")
            click.echo(f"  Files to index: {result.files_added}")
        else:
            click.echo(f"\n{colors.success('Indexing complete!')}")
            click.echo(f"  Files indexed: {result.files_added}")
            if result.files_modified > 0:
                click.echo(f"  Files modified: {result.files_modified}")
            if result.files_removed > 0:
                click.echo(f"  Files removed: {result.files_removed}")
            click.echo(f"  Chunks created: {result.chunks_added}")
            click.echo(f"  Time taken: {result.time_taken:.2f}s")
            if result.was_incremental:
                click.echo(colors.dim("  (incremental update)"))

        # Show stats if requested
        if stats and not dry_run:
            status_info = engine.get_status(directory)
            if status_info:
                click.echo(f"\n{colors.info('Index statistics:')}")
                click.echo(f"  Total files: {status_info.get('files_indexed', 0)}")
                click.echo(f"  Total chunks: {status_info.get('chunks_indexed', 0)}")
                click.echo(f"  Index size: {status_info.get('index_size_mb', 0):.2f} MB")

                chunk_types = status_info.get("chunk_types", {})
                if chunk_types:
                    click.echo(f"  Chunk types:")
                    for ctype, count in chunk_types.items():
                        click.echo(f"    {ctype}: {count}")
    else:
        click.echo(colors.error(f"Indexing failed: {result.error}"), err=True)
        sys.exit(1)
