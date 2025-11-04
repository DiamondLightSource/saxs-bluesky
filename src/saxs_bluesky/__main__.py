"""Interface for ``python -m saxs_bluesky``."""

import click

from saxs_bluesky._version import __version__
from saxs_bluesky.gui.panda_gui import PandAGUI
from saxs_bluesky.utils.utils import (
    authenticate,
    load_beamline_config,
    open_scripting,
    save_panda_cli,
)

__all__ = ["main"]


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, message="%(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        print("Please invoke subcommand!")


@main.command(name="gui")
def gui():
    config = load_beamline_config()
    PandAGUI(configuration=config.DEFAULT_EXPERIMENT)


@main.command(name="login")
def login():
    authenticate()


@main.command(name="scripts")
def scripts():
    open_scripting()


@main.command(name="save_panda")
def save_panda():
    save_panda_cli()


if __name__ == "__main__":
    main()
