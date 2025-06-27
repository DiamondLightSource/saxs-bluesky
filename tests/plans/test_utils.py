from sas_bluesky.plans.utils import FAST_DETECTORS


def test_fast_detectors_without_beamline_env_var_makes_set():
    assert FAST_DETECTORS == {"saxs", "waxs"}
