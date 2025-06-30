from sas_bluesky.beamline_configs import b21_profile, i22_profile


def test_i22_profile():
    assert len(i22_profile.DEFAULT_PROFILE.groups[0].run_pulses) == 4


def test_b21_profile():
    assert len(b21_profile.DEFAULT_PROFILE.groups[0].run_pulses) == 6
