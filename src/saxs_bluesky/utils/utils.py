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


def return_standard_detectors(beamline) -> list[StandardDetector]:
    """
    Attempt to return a list of standard detectors for the given beamline.

    Args:
        BL: The beamline module.

    Returns:
        list[StandardDetector]: List of instantiated standard detectors.
    """
    standard_detector_list = []
    exec(f"from {dodal.beamlines.__name__} import {beamline}")

    beamline_module_variables = dir(eval(beamline))

    for variable in beamline_module_variables:
        if variable.islower():  # only devices will be lowercase
            try:
                object = eval(f"{beamline}.{variable}")("", None)
                if isinstance(object, StandardDetector):
                    standard_detector_list.append(inject(variable))
            except:  # noqa
                pass

    return standard_detector_list
