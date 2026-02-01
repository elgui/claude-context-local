"""Doctor command for csearch CLI - check dependencies and configuration."""

import shutil
import sys
from pathlib import Path

import click

from core.config import Config, get_config
from core.project import ProjectManager
from cli.output.colors import ColoredOutput


def check_ok(colors: ColoredOutput, message: str) -> None:
    """Print OK check."""
    click.echo(f"  {colors.success('[OK]')} {message}")


def check_warn(colors: ColoredOutput, message: str) -> None:
    """Print warning check."""
    click.echo(f"  {colors.warning('[WARN]')} {message}")


def check_fail(colors: ColoredOutput, message: str) -> None:
    """Print failed check."""
    click.echo(f"  {colors.error('[FAIL]')} {message}")


@click.command()
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def doctor(ctx: click.Context, no_color: bool) -> None:
    """Check system dependencies and configuration.

    Runs diagnostic checks to ensure csearch is properly configured.

    \b
    Examples:
      csearch doctor                    Run all diagnostic checks
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    click.echo(colors.info("csearch Doctor"))
    click.echo()

    all_ok = True

    # Check Python version
    click.echo(colors.info("Python Environment"))
    py_version = sys.version_info
    if py_version >= (3, 12):
        check_ok(colors, f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    elif py_version >= (3, 10):
        check_warn(colors, f"Python {py_version.major}.{py_version.minor} (3.12+ recommended)")
    else:
        check_fail(colors, f"Python {py_version.major}.{py_version.minor} (3.12+ required)")
        all_ok = False
    click.echo()

    # Check core dependencies
    click.echo(colors.info("Core Dependencies"))

    # Check faiss
    try:
        import faiss
        check_ok(colors, f"faiss-cpu {faiss.__version__ if hasattr(faiss, '__version__') else 'installed'}")
    except ImportError:
        check_fail(colors, "faiss-cpu not installed")
        all_ok = False

    # Check sentence-transformers
    try:
        import sentence_transformers
        check_ok(colors, f"sentence-transformers {sentence_transformers.__version__}")
    except ImportError:
        check_fail(colors, "sentence-transformers not installed")
        all_ok = False

    # Check tree-sitter
    try:
        import tree_sitter
        check_ok(colors, f"tree-sitter {tree_sitter.__version__ if hasattr(tree_sitter, '__version__') else 'installed'}")
    except ImportError:
        check_fail(colors, "tree-sitter not installed")
        all_ok = False

    # Check fastmcp
    try:
        import fastmcp
        check_ok(colors, "fastmcp installed")
    except ImportError:
        check_warn(colors, "fastmcp not installed (needed for MCP server)")

    # Check watchdog (optional)
    try:
        import watchdog
        check_ok(colors, "watchdog installed (file watching available)")
    except ImportError:
        check_warn(colors, "watchdog not installed (file watching disabled)")
    click.echo()

    # Check optional tools
    click.echo(colors.info("Optional Tools"))

    # Check ripgrep
    if shutil.which("rg"):
        check_ok(colors, "ripgrep (rg) available for exact search")
    else:
        check_warn(colors, "ripgrep (rg) not found (falling back to grep)")

    # Check GPU support
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            check_ok(colors, f"CUDA available ({gpu_name})")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            check_ok(colors, "Apple MPS available")
        else:
            check_warn(colors, "No GPU detected (using CPU)")
    except ImportError:
        check_warn(colors, "PyTorch not found (cannot check GPU)")
    click.echo()

    # Check configuration
    click.echo(colors.info("Configuration"))
    config = get_config()
    config_path = Config.get_config_path()

    if config_path.exists():
        check_ok(colors, f"Config file: {config_path}")
    else:
        check_warn(colors, f"Config file not found (using defaults)")

    # Check storage directory
    if config.storage_dir.exists():
        check_ok(colors, f"Storage directory: {config.storage_dir}")

        # Check free space
        import os
        stat = os.statvfs(config.storage_dir)
        free_gb = (stat.f_frsize * stat.f_bavail) / (1024 ** 3)
        if free_gb > 5:
            check_ok(colors, f"Free disk space: {free_gb:.1f} GB")
        elif free_gb > 1:
            check_warn(colors, f"Low disk space: {free_gb:.1f} GB")
        else:
            check_fail(colors, f"Very low disk space: {free_gb:.1f} GB")
            all_ok = False
    else:
        check_warn(colors, f"Storage directory not created yet")
    click.echo()

    # Check model
    click.echo(colors.info("Embedding Model"))
    model_dir = config.storage_dir / "models"
    if model_dir.exists() and list(model_dir.glob("*")):
        check_ok(colors, f"Model cache: {model_dir}")

        # Check for EmbeddingGemma
        try:
            from embeddings.embedder import CodeEmbedder
            embedder = CodeEmbedder(cache_dir=str(model_dir))
            model_info = embedder.get_model_info()
            check_ok(colors, f"Model: {model_info.get('model_name', 'unknown')}")
        except Exception as e:
            check_warn(colors, f"Could not load model: {e}")
    else:
        check_warn(colors, "Model not downloaded yet (will download on first use)")
    click.echo()

    # Check indexed projects
    click.echo(colors.info("Indexed Projects"))
    projects = ProjectManager().list_projects()
    if projects:
        check_ok(colors, f"{len(projects)} project(s) indexed")
        for p in projects[:3]:
            click.echo(f"      - {p.project_name}: {p.files_indexed} files, {p.chunks_indexed} chunks")
        if len(projects) > 3:
            click.echo(f"      ... and {len(projects) - 3} more")
    else:
        check_warn(colors, "No projects indexed yet")
    click.echo()

    # Summary
    click.echo(colors.info("Summary"))
    if all_ok:
        click.echo(colors.success("  All checks passed!"))
    else:
        click.echo(colors.error("  Some checks failed. Please address the issues above."))
        sys.exit(1)
