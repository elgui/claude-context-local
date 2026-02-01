"""Config command for csearch CLI."""

import os
import subprocess
import sys
from pathlib import Path

import click

from core.config import Config, get_config
from cli.output.colors import ColoredOutput


@click.group(invoke_without_command=True)
@click.option(
    "--edit", "-e",
    is_flag=True,
    help="Open config file in $EDITOR."
)
@click.option(
    "--path",
    is_flag=True,
    help="Show config file path."
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output."
)
@click.pass_context
def config(
    ctx: click.Context,
    edit: bool,
    path: bool,
    no_color: bool,
) -> None:
    """View and manage csearch configuration.

    \b
    Examples:
      csearch config                    Show current configuration
      csearch config --edit             Open config in $EDITOR
      csearch config --path             Show config file path
      csearch config set threshold 0.5  Set a config value
    """
    use_colors = ctx.obj.get("use_colors", True) and not no_color
    colors = ColoredOutput(use_colors)
    ctx.obj["colors"] = colors

    config_path = Config.get_config_path()

    if path:
        click.echo(config_path)
        return

    if edit:
        editor = os.environ.get("EDITOR", "vim")
        if not config_path.exists():
            # Create default config
            cfg = get_config()
            cfg.save()
            click.echo(f"Created default config at: {config_path}")

        try:
            subprocess.run([editor, str(config_path)])
        except FileNotFoundError:
            click.echo(colors.error(f"Editor not found: {editor}"), err=True)
            click.echo("Set the EDITOR environment variable to your preferred editor.")
            sys.exit(1)
        return

    # If no subcommand, show current config
    if ctx.invoked_subcommand is None:
        cfg = get_config()

        click.echo(colors.info("csearch Configuration"))
        click.echo()

        click.echo(colors.info("[general]"))
        click.echo(f"  storage_dir = {cfg.storage_dir}")
        click.echo(f"  default_threshold = {cfg.default_threshold}")
        click.echo(f"  max_results = {cfg.max_results}")
        click.echo()

        click.echo(colors.info("[model]"))
        click.echo(f"  name = {cfg.model.name}")
        click.echo(f"  device = {cfg.model.device}")
        click.echo(f"  batch_size = {cfg.model.batch_size}")
        click.echo()

        click.echo(colors.info("[index]"))
        click.echo(f"  max_file_size_kb = {cfg.index.max_file_size_kb}")
        click.echo(f"  excluded_dirs = {cfg.index.excluded_dirs[:5]}...")
        click.echo()

        click.echo(colors.info("[watch]"))
        click.echo(f"  debounce_ms = {cfg.watch.debounce_ms}")
        click.echo(f"  auto_start = {cfg.watch.auto_start}")
        click.echo()

        click.echo(colors.info("[output]"))
        click.echo(f"  context_lines = {cfg.output.context_lines}")
        click.echo(f"  show_score = {cfg.output.show_score}")
        click.echo(f"  truncate_lines = {cfg.output.truncate_lines}")
        click.echo(f"  color = {cfg.output.color}")
        click.echo()

        click.echo(colors.dim(f"Config file: {config_path}"))
        if not config_path.exists():
            click.echo(colors.dim("(using defaults, file not created yet)"))


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    \b
    Examples:
      csearch config set threshold 0.5
      csearch config set model.device cuda
      csearch config set output.color always
    """
    colors = ctx.obj.get("colors", ColoredOutput(True))

    cfg = get_config()

    # Parse key path (e.g., "model.device")
    parts = key.split(".")

    try:
        if len(parts) == 1:
            # Top-level key
            if key == "threshold":
                cfg.default_threshold = float(value)
            elif key == "max_results":
                cfg.max_results = int(value)
            else:
                raise ValueError(f"Unknown key: {key}")

        elif len(parts) == 2:
            section, attr = parts
            if section == "model":
                if attr == "name":
                    cfg.model.name = value
                elif attr == "device":
                    cfg.model.device = value
                elif attr == "batch_size":
                    cfg.model.batch_size = int(value)
                else:
                    raise ValueError(f"Unknown model key: {attr}")
            elif section == "index":
                if attr == "max_file_size_kb":
                    cfg.index.max_file_size_kb = int(value)
                else:
                    raise ValueError(f"Unknown index key: {attr}")
            elif section == "watch":
                if attr == "debounce_ms":
                    cfg.watch.debounce_ms = int(value)
                elif attr == "auto_start":
                    cfg.watch.auto_start = value.lower() in ("true", "1", "yes")
                else:
                    raise ValueError(f"Unknown watch key: {attr}")
            elif section == "output":
                if attr == "context_lines":
                    cfg.output.context_lines = int(value)
                elif attr == "show_score":
                    cfg.output.show_score = value.lower() in ("true", "1", "yes")
                elif attr == "truncate_lines":
                    cfg.output.truncate_lines = int(value)
                elif attr == "color":
                    if value not in ("auto", "always", "never"):
                        raise ValueError("color must be auto, always, or never")
                    cfg.output.color = value
                else:
                    raise ValueError(f"Unknown output key: {attr}")
            else:
                raise ValueError(f"Unknown section: {section}")
        else:
            raise ValueError(f"Invalid key format: {key}")

        # Save config
        cfg.save()
        click.echo(colors.success(f"Set {key} = {value}"))

    except ValueError as e:
        click.echo(colors.error(str(e)), err=True)
        sys.exit(1)


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx: click.Context, key: str) -> None:
    """Get a configuration value.

    \b
    Examples:
      csearch config get threshold
      csearch config get model.device
    """
    colors = ctx.obj.get("colors", ColoredOutput(True))

    cfg = get_config()
    parts = key.split(".")

    try:
        if len(parts) == 1:
            if key == "threshold":
                value = cfg.default_threshold
            elif key == "max_results":
                value = cfg.max_results
            elif key == "storage_dir":
                value = cfg.storage_dir
            else:
                raise ValueError(f"Unknown key: {key}")

        elif len(parts) == 2:
            section, attr = parts
            if section == "model":
                value = getattr(cfg.model, attr, None)
            elif section == "index":
                value = getattr(cfg.index, attr, None)
            elif section == "watch":
                value = getattr(cfg.watch, attr, None)
            elif section == "output":
                value = getattr(cfg.output, attr, None)
            else:
                raise ValueError(f"Unknown section: {section}")

            if value is None:
                raise ValueError(f"Unknown key: {key}")
        else:
            raise ValueError(f"Invalid key format: {key}")

        click.echo(value)

    except ValueError as e:
        click.echo(colors.error(str(e)), err=True)
        sys.exit(1)
