"""Interface for ``python -m sas_bluesky``."""

import click
from bluesky import RunEngine

from sas_bluesky.panda_gui import PandAGUI
from sas_bluesky.stubs.panda_stubs import return_connected_device, save_device_to_yaml
from sas_bluesky.utils.utils import load_beamline_devices, load_beamline_profile

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


@main.command(name="save_panda")
def save_panda():
    RE = RunEngine()

    DEV = load_beamline_devices()
    panda_name = DEV.DEFAULT_PANDA
    connected_panda = return_connected_device("i22", panda_name)
    yaml_dir = input("Input directory to save")
    RE(
        save_device_to_yaml(
            yaml_directory=yaml_dir,
            yaml_file_name=f"{panda_name}_SAVED",
            device=connected_panda,
        )
    )  # noqa


if __name__ == "__main__":
    main()
