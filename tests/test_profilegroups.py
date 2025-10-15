import os
from pathlib import Path

from pydantic_core import from_json

from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

SAXS_bluesky_ROOT = Path(__file__)

yaml_dir = os.path.join(
    SAXS_bluesky_ROOT.parent.parent, "src", "saxs_bluesky", "profile_yamls"
)


def test_profile_loader():
    config_filepath = os.path.join(yaml_dir, "panda_config.yaml")
    config = ExperimentLoader.read_from_yaml(config_filepath)

    first_profile = config.profiles[0]

    assert isinstance(first_profile, Profile)
    assert isinstance(first_profile.groups[0], Group)


def test_profile_append():
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

    assert isinstance(profile, Profile)
    assert len(profile.groups) == 1


def test_profile_json():
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

    json_schema = profile.model_dump_json()

    profile = Profile.model_validate(profile)
    converted_profile = Profile.model_validate(
        from_json(json_schema, allow_partial=True)
    )

    assert profile.__dict__ == converted_profile.__dict__


def test_profile_delete():
    profile = Profile()

    for _i in range(5):
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

    profile.delete_group(len(profile.groups) - 1)

    assert len(profile.groups) == 4


def test_active_pulses():
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

    assert profile.active_pulses == [1, 2, 3, 4]


def test_profile_properties():
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

    profile.return_trigger_info(0.1)
    number_of_events = profile.number_of_events
    total_frames = profile.total_frames
    duration = profile.duration

    assert duration == 2
    assert total_frames == 1
    assert number_of_events == [1]


def test_profiles_in_and_outs():
    profile = Profile()

    assert len(profile.inputs()) == 8
    assert len(profile.outputs()) == 12


def test_profiles_seq_triggers():
    profile = Profile()

    profile_seq_triggers = profile.seq_triggers()

    assert len(profile_seq_triggers) == 13

    valid_triggers = (
        "IMMEDIATE",
        "BITA_0",
        "BITA_1",
        "BITB_0",
        "BITB_1",
        "BITC_0",
        "BITC_1",
        "POSA_GT",
        "POSA_LT",
        "POSB_GT",
        "POSB_LT",
        "POSC_GT",
        "POSC_LT",
    )

    for trig in valid_triggers:
        assert trig in profile_seq_triggers
