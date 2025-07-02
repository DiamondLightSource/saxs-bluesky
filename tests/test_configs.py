from sas_bluesky.defaults_configs.b21 import b21_profile
from sas_bluesky.defaults_configs.i22 import i22_profile


def test_i22_profile():
    assert len(i22_profile.DEFAULT_PROFILE.groups[0].run_pulses) == 4


def test_b21_profile():
    assert len(b21_profile.DEFAULT_PROFILE.groups[0].run_pulses) == 6
