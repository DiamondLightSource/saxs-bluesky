import os
import subprocess
from datetime import datetime
from importlib import import_module
from pathlib import Path

from blueapi.service.interface import config

############################################################################################
from dodal.common import inject
from dodal.log import LOGGER
from dodal.utils import get_beamline_name
from ophyd_async.core import StandardDetector

import saxs_bluesky.beamline_configs
import saxs_bluesky.blueapi_configs
from saxs_bluesky.stubs.panda_stubs import return_connected_device, save_device_to_yaml

DEFAULT_BEAMLINE = "i22"


def get_saxs_beamline() -> str:
    """
    Get the current SAXS beamline name from the environment or default to 'i22'.

    Returns:
        str: The beamline name.
    """
    beamline = get_beamline_name(os.getenv("BEAMLINE"))  # type: ignore

    if beamline is None:
        blueapi_metadata = config().env.metadata
        if blueapi_metadata is not None:
            beamline = blueapi_metadata.instrument
        else:
            beamline = DEFAULT_BEAMLINE
            LOGGER.info(
                f"No beamline is set in metadata. Beamline has defaulted to {beamline}"
            )

    return beamline


def get_beamline_module_name(beamline: str):
    beamline_config = f"{saxs_bluesky.beamline_configs.__name__}.{beamline}_config"

    return beamline_config


def load_beamline_config():
    """
    Dynamically import and return the beamline configuration module.

    Returns:
        module: The imported beamline configuration module.
    """
    beamline = get_saxs_beamline()
    beamline_config_path = get_beamline_module_name(beamline)

    beamline_config = import_module(beamline_config_path)
    return beamline_config


def return_standard_detectors(beamline: str) -> list[StandardDetector]:
    """
    Attempt to return a list of standard detectors for the given beamline.

    Args:
        beamline: The beamline name (e.g., "i22").

    Returns:
        list[StandardDetector]: List of instantiated standard detectors.
    """
    standard_detector_list = []
    # Import the beamline module dynamically
    beamline_module = import_module(f"dodal.beamlines.{beamline}")

    for variable in dir(beamline_module):
        if variable.islower():  # only devices will be lowercase
            try:
                obj = getattr(beamline_module, variable)("", None)
                if isinstance(obj, StandardDetector):
                    standard_detector_list.append(inject(variable))
            except Exception:
                continue

    return standard_detector_list


def get_blueapi_config_path(beamline: str | None = None):
    if beamline is None:
        beamline = get_saxs_beamline()

    blueapi_config_dir = os.path.dirname(saxs_bluesky.blueapi_configs.__file__)
    blueapi_config_path = f"{blueapi_config_dir}/{beamline}_blueapi_config.yaml"
    return blueapi_config_path


def authenticate(beamline: str | None = None):
    if beamline is None:
        beamline = get_saxs_beamline()

    blueapi_config_path = get_blueapi_config_path(beamline)
    subprocess.run(["blueapi", "-c", blueapi_config_path, "login"], shell=True)


def open_scripting(beamline: str | None = None):
    if beamline is None:
        beamline = get_saxs_beamline()

    root_path = Path(saxs_bluesky.__file__).parent.parent.parent
    example_path = os.path.join(root_path, "user_scripts", beamline)

    try:
        subprocess.run([f"module load vscode; code {example_path}"], shell=True)
    except FileNotFoundError:
        print("Scripts located at:", example_path)


def save_panda_cli(
    beamline: str | None = None,
    panda_name: str | None = None,
    yaml_name: str | None = None,
):
    from bluesky import RunEngine

    run_engine = RunEngine()

    if beamline is None:
        beamline = get_saxs_beamline()
        assert beamline is not None

    if panda_name is None:
        config = load_beamline_config()
        panda_name = config.DEFAULT_PANDA
        assert panda_name is not None

    if yaml_name is None:
        yaml_name = input("Input name suffix to save:  ")
    if (yaml_name is None) or (yaml_name == ""):
        yaml_name = datetime.now().strftime("%Y-%m-%d")

    connected_panda = return_connected_device(beamline, panda_name)

    yaml_dir = os.path.join(os.path.dirname(Path(__file__).parent), "ophyd_panda_yamls")
    yaml_filename = f"{beamline}_{panda_name}_{yaml_name}"

    run_engine(
        save_device_to_yaml(
            yaml_directory=yaml_dir,
            yaml_file_name=yaml_filename,
            device=connected_panda,
        )
    )

    print(f"Saved PandA yaml to {yaml_dir}/{yaml_filename}.yaml")
