"""

Configuration for i22 PandA beamline

"""

import os
from copy import deepcopy

from bluesky.protocols import Readable
from dodal.beamlines import p38
from dodal.common import inject
from ophyd_async.core import StandardDetector
from ophyd_async.fastcs.panda import HDFPanda

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

DEFAULT_INSTRUMENT_SESSION = "cm40643-4"

BL = p38.BL

###THESE NEED TO BE LISTS TO BE SERIALISED

FAST_DETECTORS: list[StandardDetector] = [
    inject("saxs"),
    inject("waxs"),
]

DEFAULT_PANDA: HDFPanda = inject("panda1")

DEFAULT_BASELINE: list[Readable] = []

# GUI Elements
PULSEBLOCKS = 4
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["FS", "DETS/TETS", "OAV", "Fluro"]
THEME_NAME = "clam"  # --> ('clam', 'alt', 'default', 'classic')

# PandA Wiring connections

TTLIN = {1: "", 2: None, 3: None, 4: "", 5: "", 6: ""}

TTLOUT = {
    1: "saxs",
    2: "waxs",
    3: None,
    4: None,
    5: None,
    6: None,
    7: None,
    8: None,
    9: None,
    10: None,
}


LVDSIN = {1: None, 2: None}


LVDSOUT = {1: None, 2: None}

PULSE_CONNECTIONS = {
    1: [TTLOUT[1]],
    2: [TTLOUT[2], TTLOUT[3]],
    3: [TTLOUT[4]],
    4: [TTLOUT[5]],
    5: [TTLOUT[6]],
    6: [TTLOUT[7]],
}


"""
# ncd plan parameters
"""

DEADTIME_BUFFER = 20e-6  # Buffer added to deadtime to handle minor discrepencies between detector and panda clocks #noqa
DEFAULT_SEQ = 1  # default sequencer is this one, pandas can have 2
CONFIG_NAME = "PandaTrigger"


"""
# DEFAULT PROFILES
"""

DEFAULT_GROUP = Group(
    frames=1,
    trigger="IMMEDIATE",
    wait_time=10,
    wait_units="MS",
    run_time=100,
    run_units="MS",
    wait_pulses=[0, 0, 0, 0],
    run_pulses=[1, 1, 1, 1],
)


DEFAULT_PROFILE = Profile(
    repeats=1,
    seq_trigger="IMMEDIATE",
    groups=[deepcopy(DEFAULT_GROUP)],
    multiplier=[1, 1, 1, 1],
)

DEFAULT_EXPERIMENT = ExperimentLoader(
    profiles=[deepcopy(DEFAULT_PROFILE)],
    instrument=p38.BL,
    detectors=FAST_DETECTORS,
    instrument_session=DEFAULT_INSTRUMENT_SESSION,
)


blueapi_config_path = (
    f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"
)
CLIENT = BlueAPIPythonClient(BL, blueapi_config_path, DEFAULT_INSTRUMENT_SESSION)
