import os
import subprocess
from importlib import import_module

from blueapi.service.interface import config

############################################################################################
from dodal.common import inject
from dodal.log import LOGGER
from dodal.utils import get_beamline_name
from ophyd_async.core import StandardDetector

import saxs_bluesky.beamline_configs
import saxs_bluesky.blueapi_configs

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

        os.environ["BEAMLINE"] = beamline

    return beamline


def load_beamline_config():
    """
    Dynamically import and return the beamline configuration module.

    Returns:
        module: The imported beamline configuration module.
    """
    beamline = get_saxs_beamline()

    beamline_config = import_module(
        f"{saxs_bluesky.beamline_configs.__name__}.{beamline}_config"
    )
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


def get_config_path(beamline: str | None = None):
    if beamline is None:
        beamline = get_saxs_beamline()

    blueapi_config_dir = os.path.dirname(saxs_bluesky.blueapi_configs.__file__)

    blueapi_config_path = f"{blueapi_config_dir}/{beamline}_blueapi_config.yaml"

    return blueapi_config_path


def authenticate(beamline: str | None = None):
    if beamline is None:
        beamline = get_saxs_beamline()

    blueapi_config_path = get_config_path(beamline)

    subprocess.run(["blueapi", "-c", blueapi_config_path, "login"])
