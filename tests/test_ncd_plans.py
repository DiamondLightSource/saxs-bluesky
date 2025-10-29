from pathlib import Path

import pytest

# import pytest_asyncio
from bluesky import RunEngine
from dodal.common.beamlines.beamline_utils import get_path_provider, set_path_provider
from dodal.common.visit import LocalDirectoryServiceClient, StaticVisitPathProvider
from ophyd_async.core import TriggerInfo, init_devices
from ophyd_async.epics.adpilatus import PilatusDetector
from ophyd_async.fastcs.panda import HDFPanda

from saxs_bluesky.plans.ncd_panda import (
    append_group,
    configure_panda_triggering,
    create_profile,
    create_steps,
    delete_group,
    generate_repeated_trigger_info,
    get_profile,
    get_trigger_info,
    return_deadtime,
    set_trigger_info,
)
from saxs_bluesky.stubs.panda_stubs import get_settings_dir_and_name
from saxs_bluesky.utils.profile_groups import Group, Profile

#     get_trigger_info,
#     log_detectors,
#     set_detectors,
#     set_profile,
#     set_trigger_info,
# )


# @pytest.fixture
# def path_provider():

set_path_provider(
    StaticVisitPathProvider(
        "ixx",
        Path("/dls/ixx/data/2025/cm12356-1/"),
        client=LocalDirectoryServiceClient(),
    )
)


@pytest.fixture
def valid_profile() -> Profile:
    valid_profile = Profile()

    for _ in range(3):
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
def valid_profile_with_multiplier() -> Profile:
    valid_profile = Profile(multiplier=[1, 2, 4, 8])

    for _ in range(3):
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
def run_engine() -> RunEngine:
    return RunEngine()


@pytest.fixture
async def panda(run_engine: RunEngine) -> HDFPanda:
    async with init_devices(connect=True, mock=True):
        panda = HDFPanda(prefix="ixx-test-panda", path_provider=get_path_provider())

    return panda


@pytest.fixture
async def pilatus(run_engine: RunEngine) -> PilatusDetector:
    async with init_devices(connect=True, mock=True):
        pilatus = PilatusDetector(
            prefix="ixx-test-pilatus", path_provider=get_path_provider()
        )

    return pilatus


def test_profile_manipulation(run_engine: RunEngine):
    def test_manipulation():
        yield from create_profile(repeats=1)
        yield from append_group()
        yield from append_group()

        profile = get_profile()

        assert profile is not None

        assert profile.n_groups == 2

        yield from delete_group(1)

        assert profile.n_groups == 1

    run_engine(test_manipulation())


@pytest.mark.parametrize(
    "start, stop, step",
    ([1, 5, 1], [1, 5, 0.1], [1, 5, None], [1, None, None], [5, 1, 0.1]),
)
def test_create_steps(start, stop, step):
    steps = create_steps(start, stop, step)
    assert len(steps) > 0

    if step:
        assert len(steps) > 1


def test_panda_configure(
    run_engine: RunEngine,
    panda: HDFPanda,
    pilatus: PilatusDetector,
    valid_profile: Profile,
):
    detectors = [pilatus]

    run_engine(
        configure_panda_triggering(
            profile=valid_profile,
            panda=panda,
            detectors=detectors,  # type: ignore
            ensure_panda_connected=False,
            force_load=False,
        )
    )


# def test_panda_configure_and_run(
#     run_engine: RunEngine,
#     panda: HDFPanda,
#     pilatus: PilatusDetector,
#     valid_profile: Profile,
# ):
#     detectors = [pilatus]

#     run_engine(
#         configure_and_run_panda_triggering(
#             profile=valid_profile,
#             panda=panda,
#             detectors=detectors,  # type: ignore
#             ensure_panda_connected=False,
#         )
#     )


def test_return_deadtime(panda: HDFPanda, pilatus: PilatusDetector):
    detectors = [panda, pilatus]

    deadtime_array = return_deadtime(detectors)

    assert len(deadtime_array) == len(detectors)


def test_generate_repeated_trigger_info(
    valid_profile_with_multiplier: Profile,
):
    trigger_info_list = generate_repeated_trigger_info(
        profile=valid_profile_with_multiplier, max_deadtime=0.1, livetime=1
    )

    assert len(trigger_info_list) > 1


def test_get_settings_dir_and_name():
    beamline = "i22"
    settings_name = "PandaTrigger"
    panda_name = "panda1"

    yaml_dir, yaml_name = get_settings_dir_and_name(beamline, settings_name, panda_name)

    assert yaml_name == f"{beamline}_{settings_name}_{panda_name}"


def test_set_and_get_trigger_info(run_engine: RunEngine):
    trigger_info = TriggerInfo(number_of_events=10, deadtime=0.1, livetime=1)

    def test_trig():
        yield from set_trigger_info(trigger_info)
        returned_trigger_info = get_trigger_info()

        assert returned_trigger_info is not None

        assert returned_trigger_info.number_of_events == 10
        assert returned_trigger_info.deadtime == 0.1
        assert returned_trigger_info.livetime == 1

    run_engine(test_trig())
