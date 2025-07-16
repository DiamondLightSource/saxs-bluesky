import os
from pathlib import Path

from sas_bluesky.profile_groups import Group, Profile
from sas_bluesky.utils.utils import ProfilePlotter, load_beamline_devices

os.environ["BEAMLINE"] = "i22"

DEV = load_beamline_devices()
FAST_DETECTORS = DEV.FAST_DETECTORS

SAS_bluesky_ROOT = Path(__file__)

yaml_dir = os.path.join(
    SAS_bluesky_ROOT.parent.parent, "src", "sas_bluesky", "profile_yamls"
)


def test_profile_append():
    P = Profile()
    P.append_group(
        Group(
            frames=1,
            wait_time=1,
            wait_units="S",
            run_time=1,
            run_units="S",
            pause_trigger="IMMEDIATE",
            wait_pulses=[0, 0, 0, 0],
            run_pulses=[1, 1, 1, 1],
        )
    )

    time, signal = ProfilePlotter.generate_pulse_signal(P, 1)
    assert len(time) == len(signal)


def test_fast_detectors_without_beamline_env_var_makes_set():
    assert "saxs" in FAST_DETECTORS
    assert "waxs" in FAST_DETECTORS
    assert len(FAST_DETECTORS) == 2
