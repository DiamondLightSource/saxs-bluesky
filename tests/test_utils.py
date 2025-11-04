import os

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.plotter import ProfilePlotter
from saxs_bluesky.utils.profile_groups import Group, Profile
from saxs_bluesky.utils.utils import (
    get_blueapi_config_path,
    load_beamline_config,
    return_standard_detectors,
)

CONFIG = load_beamline_config()
FAST_DETECTORS = CONFIG.FAST_DETECTORS


def test_profile_plotter():
    profile = Profile()
    profile.append_group(
        Group(
            frames=1,
            trigger="IMMEDIATE",
            wait_time=1,
            wait_units="S",
            run_time=1,
            run_units="S",
            wait_pulses=[0, 0, 0, 0],
            run_pulses=[1, 1, 1, 1],
        )
    )

    time, signal = ProfilePlotter.generate_pulse_signal(profile, 1)
    assert len(time) == len(signal)


def test_fast_detectors_without_beamline_env_var_makes_set():
    assert "saxs" in FAST_DETECTORS
    assert "waxs" in FAST_DETECTORS
    assert len(FAST_DETECTORS) == 4


def test_return_standard_detectors():
    standard_detector_list_i22 = return_standard_detectors("i22")
    assert "saxs" in standard_detector_list_i22


def test_get_blueapi_config_path():
    beamline = "i22"

    config_path = get_blueapi_config_path("i22")

    blueapi_config_dir = os.path.dirname(saxs_bluesky.blueapi_configs.__file__)
    blueapi_config_path = f"{blueapi_config_dir}/{beamline}_blueapi_config.yaml"

    assert config_path == blueapi_config_path
