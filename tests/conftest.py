import os
from pathlib import Path

import pytest
from bluesky import RunEngine
from dodal.common.beamlines.beamline_utils import get_path_provider, set_path_provider
from dodal.common.visit import LocalDirectoryServiceClient, StaticVisitPathProvider
from ophyd_async.core import AsyncStatus, TriggerInfo, init_devices
from ophyd_async.epics.adpilatus import PilatusDetector
from ophyd_async.fastcs.panda import HDFPanda

SAXS_bluesky_ROOT = Path(__file__)

YAML_DIR = os.path.join(
    SAXS_bluesky_ROOT.parent.parent, "src", "saxs_bluesky", "profile_yamls"
)


set_path_provider(
    StaticVisitPathProvider(
        "ixx",
        Path(os.path.dirname(__file__)),
        client=LocalDirectoryServiceClient(),
    )
)


@pytest.fixture
def run_engine() -> RunEngine:
    return RunEngine()


@AsyncStatus.wrap
async def mock_prepare(value: TriggerInfo):
    pass


@pytest.fixture
async def panda() -> HDFPanda:
    async with init_devices(connect=True, mock=True):
        panda = HDFPanda(prefix="ixx-test-panda", path_provider=get_path_provider())

    panda.prepare = mock_prepare

    return panda


@pytest.fixture
async def pilatus() -> PilatusDetector:
    async with init_devices(connect=True, mock=True):
        pilatus = PilatusDetector(
            prefix="ixx-test-pilatus", path_provider=get_path_provider()
        )

    pilatus.prepare = mock_prepare

    return pilatus
