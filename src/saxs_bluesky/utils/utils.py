import os
from importlib import import_module

import dodal.beamlines
from blueapi.service.interface import config

############################################################################################
from dodal.common import inject
from dodal.log import LOGGER
from dodal.utils import get_beamline_name
from ophyd_async.core import StandardDetector

import saxs_bluesky.beamline_configs

DEFAULT_BEAMLINE = "i22"


def get_saxs_beamline() -> str:
    """
    Get the current SAXS beamline name from the environment or default to 'i22'.

    Returns:
        str: The beamline name.
    """
    BL = get_beamline_name(os.getenv("BEAMLINE"))  # type: ignore

    if BL is None:
        try:
            BLconfig = config()
            BL = BLconfig.env.metadata.instrument  # type: ignore
        except OSError as e:
            BL = DEFAULT_BEAMLINE
            LOGGER.info(
                f"No beamline is set in metadata. Beamline has defaulted to {BL}:{e}"
            )

        os.environ["BEAMLINE"] = BL

    return BL


def load_beamline_config():
    """
    Dynamically import and return the beamline configuration module.

    Returns:
        module: The imported beamline configuration module.
    """
    BL = get_saxs_beamline()

    BL_CONFIG = import_module(f"{saxs_bluesky.beamline_configs.__name__}.{BL}_config")
    return BL_CONFIG


def return_standard_detectors(BL) -> list[StandardDetector]:
    """
    Attempt to return a list of standard detectors for the given beamline.

    Args:
        BL: The beamline module.

    Returns:
        list[StandardDetector]: List of instantiated standard detectors.
    """
    standard_detector_list = []
    exec(f"from {dodal.beamlines.__name__} import {BL}")

    beamline_module_variables = dir(eval(BL))

    for variable in beamline_module_variables:
        if variable.islower():  # only devices will be lowercase
            try:
                object = eval(f"{BL}.{variable}")("", None)
                if isinstance(object, StandardDetector):
                    standard_detector_list.append(inject(variable))
            except:  # noqa
                pass

    return standard_detector_list
