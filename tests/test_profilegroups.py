import os
from pathlib import Path

import pytest
from ophyd_async.core import TriggerInfo
from ophyd_async.fastcs.panda import SeqTable
from pydantic_core import from_json

from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

SAXS_bluesky_ROOT = Path(__file__)

yaml_dir = os.path.join(
    SAXS_bluesky_ROOT.parent.parent, "src", "saxs_bluesky", "profile_yamls"
)


@pytest.fixture
def valid_profile():
    valid_profile = Profile(repeats=2)
    for _ in range(5):
        valid_profile.append_group(
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
    return valid_profile


@pytest.fixture
def valid_experiment():
    config_filepath = os.path.join(yaml_dir, "tfg3_experiments.yaml")
    valid_experiment = ExperimentLoader.read_from_yaml(config_filepath)

    return valid_experiment


def test_experiment_loader(valid_experiment: ExperimentLoader):
    first_profile = valid_experiment.profiles[0]

    assert isinstance(first_profile, Profile)
    assert isinstance(first_profile.groups[0], Group)


def test_experiment_loader_delete(valid_experiment: ExperimentLoader):
    assert valid_experiment.n_profiles == 6

    valid_experiment.delete_profile(0)

    assert valid_experiment.n_profiles == 5


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
    assert profile.n_groups == 1


def test_profile_insert(valid_profile: Profile):
    insert_group = Group(
        frames=99,
        trigger="IMMEDIATE",
        wait_time=1,
        wait_units="S",
        run_time=1,
        run_units="S",
        wait_pulses=[0, 0, 0, 0],
        run_pulses=[1, 1, 1, 1],
    )

    valid_profile.insert_group(0, insert_group)

    assert isinstance(valid_profile, Profile)
    assert valid_profile.groups[0].frames == 99


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


def test_profile_delete(valid_profile: Profile):
    valid_profile.delete_group(len(valid_profile.groups) - 1)

    assert len(valid_profile.groups) == 4


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


def test_profile_properties(valid_profile: Profile):
    trigger_info = valid_profile.return_trigger_info(0.1)
    sequence_table = valid_profile.seq_table

    number_of_events = valid_profile.number_of_events
    total_frames = valid_profile.total_frames
    duration = valid_profile.duration
    duration_per_repeat = valid_profile.duration_per_repeat

    assert isinstance(trigger_info, TriggerInfo)
    assert isinstance(sequence_table, SeqTable)

    assert duration_per_repeat == 10
    assert duration == 20
    assert total_frames == 5
    assert number_of_events == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # 5 groups, 2 repeats


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
