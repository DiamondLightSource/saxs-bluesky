"""Interface for ``python -m saxs_bluesky``."""

import os
from datetime import datetime
from pathlib import Path

import click
from bluesky import RunEngine

from saxs_bluesky._version import __version__
from saxs_bluesky.gui.panda_gui import PandAGUI
from saxs_bluesky.stubs.panda_stubs import return_connected_device, save_device_to_yaml
from saxs_bluesky.utils.utils import (
    authenticate,
    get_saxs_beamline,
    load_beamline_config,
    open_scripting,
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
def save_panda(beamline: str | None = None, panda_name: str | None = None):
    run_engine = RunEngine()

    if beamline is None:
        beamline = get_saxs_beamline()
        assert beamline is not None

    if panda_name is None:
        config = load_beamline_config()
        panda_name = config.DEFAULT_PANDA
        assert panda_name is not None

    connected_panda = return_connected_device(beamline, panda_name)
    yaml_name = input("Input name suffix to save:  ")

    if (yaml_name is None) or (yaml_name == ""):
        yaml_name = datetime.now().strftime("%Y-%m-%d")

    yaml_dir = os.path.join(os.path.dirname(Path(__file__)), "ophyd_panda_yamls")
    yaml_filename = f"{beamline}_{panda_name}_{yaml_name}"

    run_engine(
        save_device_to_yaml(
            yaml_directory=yaml_dir,
            yaml_file_name=yaml_filename,
            device=connected_panda,
        )
    )

    print(f"Saved PandA yaml to {yaml_dir}/{yaml_filename}.yaml")


if __name__ == "__main__":
    main()
