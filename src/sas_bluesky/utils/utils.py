import os
from importlib import import_module

from dodal.utils import get_beamline_name

############################################################################################

BL = get_beamline_name(os.environ["BEAMLINE"])


def load_beamline_config():
    BL_CONFIG = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_config")
    return BL_CONFIG


def load_beamline_profile():
    BL_PROF = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_profile")
    return BL_PROF


def load_beamline_detectors():
    BL_DET = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_detectors")
    return BL_DET
