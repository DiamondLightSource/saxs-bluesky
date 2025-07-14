import os

from sas_bluesky.utils.utils import load_beamline_devices

os.environ["BEAMLINE"] = "i22"

DEV = load_beamline_devices()
FAST_DETECTORS = DEV.FAST_DETECTORS


def test_fast_detectors_without_beamline_env_var_makes_set():
    assert FAST_DETECTORS == {"saxs", "waxs"}
