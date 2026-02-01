"""Search command for csearch CLI."""

import sys
import time
from pathlib import Path

import click

from core.search_engine import SearchEngine
from cli.output.formatters import get_formatter


@click.command()
@click.argument("query")
@click.option(
    "-m", "--max-results",
    type=int,
    default=10,
    help="Maximum number of results to return."
)
@click.option(
    "-f", "--file-pattern",
    type=str,
    default=None,
    help="Glob pattern to filter files (e.g., '*.py', 'src/**')."
)
@click.option(
    "-l", "--language",
    type=str,
    default=None,
    help="Filter by programming language (e.g., python, javascript, go)."
)
@click.option(
    "-t", "--chunk-type",
    type=click.Choice(["function", "class", "method", "module"]),
    default=None,
    help="Filter by chunk type."
)
@click.option(
    "--threshold",
    type=float,
    default=0.0,
    help="Minimum similarity score (0-1)."
)
@click.option(
    "-C", "--context",
    type=int,
    default=0,
    help="Number of context lines to show."
)
@click.option(
    "-s", "--sort",
    type=click.Choice(["score", "path", "line"]),
    default="score",
    help="Sort results by score, path, or line number."
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON."
)
@click.option(
    "-1", "--compact",
    is_flag=True,
    help="Compact output (path:line only, one per line)."
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with scores and metadata."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.option(
    "--exact",
    is_flag=True,
    help="Use exact text matching instead of semantic search."
)
@click.option(
    "--hybrid",
    type=str,
    default=None,
    help="Hybrid mode: semantic search filtered by exact pattern."
)
@click.option(
    "-p", "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project directory to search in."
)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    max_results: int,
    file_pattern: str,
    language: str,
    chunk_type: str,
    threshold: float,
    context: int,
    sort: str,
    output_json: bool,
    compact: bool,
    verbose: bool,
    no_color: bool,
    exact: bool,
    hybrid: str,
    project: Path,
) -> None:
    """Search for code semantically.

    QUERY is a natural language description of the code you're looking for.

    \b
    Examples:
      csearch "authentication handling"
      csearch -m 20 "where is rate limiting implemented"
      csearch -f "*.py" "async database operations"
      csearch --exact "handleUserLogin"
      csearch --hybrid "authentication" "JWT"
    """
    start_time = time.time()

    # Determine output format
    if output_json:
        format_type = "json"
    elif compact:
        format_type = "compact"
    elif verbose:
        format_type = "verbose"
    else:
        format_type = "grep"

    # Determine color usage
    use_colors = ctx.obj.get("use_colors", True) and not no_color

    # Get formatter
    formatter = get_formatter(
        format_type=format_type,
        use_colors=use_colors,
        context_lines=context,
    )

    # Initialize search engine
    engine = SearchEngine()

    # Determine project path
    project_path = project or Path.cwd()

    # Exact search doesn't require indexing
    if exact:
        results = engine.search_exact(
            pattern=query,
            project_path=project_path,
            file_pattern=file_pattern,
        )
    else:
        # Check if project is indexed for semantic search
        status = engine.get_status(project_path)
        if status is None:
            click.echo(
                f"Project not indexed: {project_path}\n"
                f"Run 'csearch index' first to index the project.",
                err=True
            )
            sys.exit(1)

        # Perform search based on mode
        if hybrid:
            results = engine.search_hybrid(
                semantic_query=query,
                exact_pattern=hybrid,
                project_path=project_path,
                max_results=max_results,
            )
        else:
            results = engine.search(
                query=query,
                project_path=project_path,
                max_results=max_results,
                threshold=threshold,
                file_pattern=file_pattern,
                language=language,
                chunk_type=chunk_type,
            )

    # Sort results if needed
    if sort == "path":
        results.sort(key=lambda r: (r.relative_path, r.line_start))
    elif sort == "line":
        results.sort(key=lambda r: (r.relative_path, r.line_start))
    # Default is score, which is already sorted

    # Calculate elapsed time
    elapsed_ms = (time.time() - start_time) * 1000

    # Format and output results
    output = formatter.format_results(results, query, elapsed_ms)
    if output:
        click.echo(output)

    # Exit with appropriate code
    if not results:
        sys.exit(1)
