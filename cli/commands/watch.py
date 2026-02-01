"""Watch command for csearch CLI - filesystem watching with auto-reindex."""

import os
import sys
import signal
import time
import logging
from pathlib import Path
from typing import Optional, Set

import click

from core.config import get_config
from core.search_engine import SearchEngine
from core.project import ProjectManager
from cli.output.colors import ColoredOutput

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches filesystem for changes and triggers reindexing."""

    def __init__(
        self,
        project_path: Path,
        debounce_ms: int = 2000,
        verbose: bool = False,
    ):
        """Initialize file watcher.

        Args:
            project_path: Path to watch.
            debounce_ms: Milliseconds to wait before reindexing.
            verbose: Whether to log file changes.
        """
        self.project_path = project_path
        self.debounce_ms = debounce_ms
        self.verbose = verbose
        self.engine = SearchEngine()
        self.config = get_config()
        self.pending_changes: Set[Path] = set()
        self.last_change_time: float = 0
        self.running = False

    def start(self) -> None:
        """Start watching for changes."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent
        except ImportError:
            raise click.ClickException(
                "watchdog package not installed. Install with: pip install watchdog"
            )

        class ChangeHandler(FileSystemEventHandler):
            def __init__(handler_self, watcher: "FileWatcher"):
                handler_self.watcher = watcher

            def on_any_event(handler_self, event: FileSystemEvent) -> None:
                if event.is_directory:
                    return

                # Get the path
                path = Path(event.src_path)

                # Skip excluded directories
                for part in path.parts:
                    if part in handler_self.watcher.config.index.excluded_dirs:
                        return

                # Skip excluded extensions
                if path.suffix in handler_self.watcher.config.index.excluded_extensions:
                    return

                # Skip hidden files
                if path.name.startswith("."):
                    return

                # Add to pending changes
                handler_self.watcher.pending_changes.add(path)
                handler_self.watcher.last_change_time = time.time()

                if handler_self.watcher.verbose:
                    event_type = event.event_type
                    logger.info(f"File {event_type}: {path}")

        self.running = True
        handler = ChangeHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.project_path), recursive=True)
        observer.start()

        click.echo(f"Watching for changes in: {self.project_path}")
        click.echo(f"Debounce: {self.debounce_ms}ms")
        click.echo("Press Ctrl+C to stop.\n")

        try:
            while self.running:
                time.sleep(0.1)

                # Check if we should process pending changes
                if self.pending_changes:
                    elapsed = (time.time() - self.last_change_time) * 1000
                    if elapsed >= self.debounce_ms:
                        self._process_changes()

        except KeyboardInterrupt:
            pass
        finally:
            observer.stop()
            observer.join()
            self.running = False

    def _process_changes(self) -> None:
        """Process pending file changes."""
        if not self.pending_changes:
            return

        change_count = len(self.pending_changes)
        self.pending_changes.clear()

        click.echo(f"\n[{time.strftime('%H:%M:%S')}] {change_count} file(s) changed, reindexing...")

        result = self.engine.index(
            project_path=self.project_path,
            force_full=False,
        )

        if result.success:
            if result.chunks_added > 0 or result.chunks_removed > 0:
                click.echo(
                    f"  Updated: +{result.chunks_added} -{result.chunks_removed} chunks "
                    f"({result.time_taken:.2f}s)"
                )
            else:
                click.echo(f"  No index changes ({result.time_taken:.2f}s)")
        else:
            click.echo(f"  Error: {result.error}", err=True)

    def stop(self) -> None:
        """Stop watching."""
        self.running = False


def daemonize(pid_file: Path, log_file: Optional[Path] = None) -> None:
    """Fork process to run as daemon."""
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)
    except OSError as e:
        raise click.ClickException(f"Fork failed: {e}")

    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)
    except OSError as e:
        raise click.ClickException(f"Second fork failed: {e}")

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "r") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
    else:
        with open("/dev/null", "w") as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())

    # Write PID file
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option(
    "--daemon", "-d",
    is_flag=True,
    help="Run as a background daemon."
)
@click.option(
    "--stop",
    "stop_daemon",
    is_flag=True,
    help="Stop the running daemon."
)
@click.option(
    "--status",
    "check_status",
    is_flag=True,
    help="Check if daemon is running."
)
@click.option(
    "--debounce",
    type=int,
    default=2000,
    help="Milliseconds to wait before reindexing (default: 2000)."
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Log file changes."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def watch(
    ctx: click.Context,
    directory: Path,
    daemon: bool,
    stop_daemon: bool,
    check_status: bool,
    debounce: int,
    verbose: bool,
    no_color: bool,
) -> None:
    """Watch for file changes and auto-reindex.

    DIRECTORY is the path to watch. Defaults to current directory.

    \b
    Examples:
      csearch watch                     Watch current directory
      csearch watch /path/to/project    Watch specific directory
      csearch watch --daemon            Run as background daemon
      csearch watch --stop              Stop the daemon
      csearch watch --status            Check daemon status
      csearch watch --debounce 5000     Wait 5 seconds before reindexing
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)

    directory = directory.resolve()

    # Get project config for PID file
    project_manager = ProjectManager()
    project_config = project_manager.get_project_config(directory)
    pid_file = project_config.watcher_pid_file
    log_file = project_config.storage_dir / "watcher.log"

    if check_status:
        # Check if daemon is running
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)  # Check if process exists
                click.echo(colors.success(f"Watcher is running (pid {pid})"))
            except (OSError, ValueError):
                click.echo(colors.warning("Watcher is not running (stale PID file)"))
                pid_file.unlink(missing_ok=True)
        else:
            click.echo("Watcher is not running")
        return

    if stop_daemon:
        # Stop the daemon
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                click.echo(colors.success(f"Stopped watcher (pid {pid})"))
                pid_file.unlink(missing_ok=True)
            except (OSError, ValueError) as e:
                click.echo(colors.warning(f"Could not stop watcher: {e}"))
                pid_file.unlink(missing_ok=True)
        else:
            click.echo("Watcher is not running")
        return

    # Check if project is indexed
    if not project_config.is_indexed():
        click.echo(colors.warning(f"Project not indexed: {directory}"))
        click.echo("Indexing now...")
        engine = SearchEngine()
        result = engine.index(project_path=directory)
        if not result.success:
            click.echo(colors.error(f"Indexing failed: {result.error}"), err=True)
            sys.exit(1)
        click.echo(colors.success("Indexing complete!"))
        click.echo()

    if daemon:
        # Check if already running
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                click.echo(colors.warning(f"Watcher already running (pid {pid})"))
                return
            except (OSError, ValueError):
                pid_file.unlink(missing_ok=True)

        # Daemonize
        click.echo(f"Starting watcher daemon for: {directory}")
        daemonize(pid_file, log_file)

        # Set up logging for daemon
        logging.basicConfig(
            level=logging.INFO if verbose else logging.WARNING,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    # Start watching
    watcher = FileWatcher(
        project_path=directory,
        debounce_ms=debounce,
        verbose=verbose,
    )

    # Handle signals
    def handle_signal(sig, frame):
        watcher.stop()
        if daemon:
            pid_file.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        watcher.start()
    finally:
        if daemon:
            pid_file.unlink(missing_ok=True)
