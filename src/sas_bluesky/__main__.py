"""Interface for ``python -m sas_bluesky``."""

import click

from sas_bluesky.panda_gui import PandAGUI
from sas_bluesky.utils.utils import load_beamline_profile

from . import __version__

__all__ = ["main"]


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, message="%(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        print("Please invoke subcommand!")


@main.command(name="start_gui")
def start_gui():
    PROF = load_beamline_profile()
    PandAGUI(configuration=PROF.DEFAULT_EXPERIMENT)


if __name__ == "__main__":
    main()
