import os
from importlib import import_module

from dodal.utils import get_beamline_name

############################################################################################


def get_sas_beamline() -> str:
    BL = get_beamline_name(os.getenv("BEAMLINE"))  # type: ignore

    if BL is None:
        BL = "i22"
        os.environ["BEAMLINE"] = BL

    return BL


BL = get_sas_beamline()


def load_beamline_config():
    BL_CONFIG = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_config")
    return BL_CONFIG


def load_beamline_profile():
    BL_PROF = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_profile")
    return BL_PROF


def load_beamline_devices():
    BL_DEV = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_dev")
    return BL_DEV
