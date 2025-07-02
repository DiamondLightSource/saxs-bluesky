from dodal.beamlines import i22
from dodal.common.beamlines.beamline_utils import get_path_provider

from sas_bluesky.profile_groups import ExperimentProfiles, Group, Profile

PP = get_path_provider()
visit_id = PP._root  # type: ignore #noqa


DEFAULT_GROUP = Group(
    frames=1,
    wait_time=1,
    wait_units="S",
    run_time=1,
    run_units="S",
    pause_trigger="IMMEDIATE",
    wait_pulses=[0, 0, 0, 0],
    run_pulses=[1, 1, 1, 1],
)


DEFAULT_PROFILE = Profile(
    cycles=1, seq_trigger="IMMEDIATE", groups=[DEFAULT_GROUP], multiplier=[1, 1, 1, 1]
)

DEFAULT_EXPERIMENT = ExperimentProfiles(
    profiles=[DEFAULT_PROFILE],
    instrument=i22.BL,
    experiment=str(visit_id),
    detectors=["saxs", "waxs"],
)
