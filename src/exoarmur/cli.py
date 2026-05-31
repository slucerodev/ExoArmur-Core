"""ExoArmur Core CLI.

Minimal CLI for ExoArmur-Core deterministic governance and replayable audit layer.
"""

import sys
from typing import Optional

import click

from exoarmur import __version__


@click.group()
@click.version_option(version=__version__, prog_name="exoarmur")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """ExoArmur Core – deterministic governance and replayable audit layer for execution.

    Core provides:
    - Deterministic execution governance
    - Replayable audit evidence chains
    - Plugin-capable executor architecture
    - Local execution without network dependencies

    For integration documentation, see: https://github.com/slucerodev/ExoArmur-Core
    """
    ctx.ensure_object(dict)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show ExoArmur Core version information."""
    click.echo(f"ExoArmur Core version: {__version__}")


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show ExoArmur Core information."""
    click.echo("ExoArmur Core")
    click.echo(f"Version: {__version__}")
    click.echo("")
    click.echo("Core capabilities:")
    click.echo("  - Deterministic execution governance")
    click.echo("  - Replayable audit evidence chains")
    click.echo("  - Plugin-capable executor architecture")
    click.echo("  - Local execution without network dependencies")
    click.echo("")
    click.echo(
        "For integration documentation, see: https://github.com/slucerodev/ExoArmur-Core"
    )


def main() -> int:
    """Main entry point for ExoArmur CLI."""
    cli()
    return 0


if __name__ == "__main__":
    sys.exit(main())
