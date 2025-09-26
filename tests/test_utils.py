from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import Group, Profile
from saxs_bluesky.utils.utils import ProfilePlotter, load_beamline_config

CONFIG = load_beamline_config()
FAST_DETECTORS = CONFIG.FAST_DETECTORS


def test_profile_plotter():
    P = Profile()
    P.append_group(
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

    time, signal = ProfilePlotter.generate_pulse_signal(P, 1)
    assert len(time) == len(signal)


def test_fast_detectors_without_beamline_env_var_makes_set():
    assert "saxs" in FAST_DETECTORS
    assert "waxs" in FAST_DETECTORS
    assert len(FAST_DETECTORS) == 4


def test_blueapi_client():
    BL = "i22"
    blueapi_config_path = f"./src/saxs_bluesky/blueapi_configs/{BL}_blueapi_config.yaml"
    client = BlueAPIPythonClient(BL, blueapi_config_path, "None")

    assert client.BL == "i22"
    client.change_session("9999")
    assert client.instrument_session == "9999"
