"""

Configuration for i22 PandA beamline

"""

from copy import deepcopy

from bluesky.protocols import Readable
from dodal.beamlines import i22
from dodal.common import inject
from ophyd_async.core import StandardDetector
from ophyd_async.fastcs.panda import HDFPanda

from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

DEFAULT_INSTRUMENT_SESSION = "cm40643-4"

###THESE NEED TO BE LISTS TO BE SERIALISED

FAST_DETECTORS: list[StandardDetector] = [
    inject("saxs"),
    inject("waxs"),
    inject("i0"),
    inject("it"),
]

DEFAULT_PANDA: HDFPanda = inject("panda1")

DEFAULT_BASELINE: list[Readable] = [
    inject("fswitch"),
    inject("slits_1"),
    inject("slits_2"),
    inject("slits_3"),
    inject("slits_4"),
    inject("slits_5"),
    inject("slits_6"),
    inject("hfm"),
    inject("vfm"),
    inject("undulator"),
    inject("dcm"),
    inject("synchrotron"),
]

# GUI Elements
PULSEBLOCKS = 4
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["FS", "DETS/TETS", "OAV", "Fluro"]
THEME_NAME = "clam"  # --> ('clam', 'alt', 'default', 'classic')

# PandA Wiring connections

TTLIN = {1: "TFG Det", 2: "TFG FS", 3: None, 4: None, 5: None, 6: None}

TTLOUT = {
    1: "i0",
    2: "FS",
    3: "oav",
    4: "User Tet",
    5: "waxs",
    6: "it",
    7: "saxs",
    8: "Fluores",
    9: "User1",
    10: "User2",
}


LVDSIN = {1: None, 2: None}
LVDSOUT = {1: None, 2: None}

PULSE_CONNECTIONS = {
    1: [TTLOUT[2]],
    2: [TTLOUT[1], TTLOUT[4], TTLOUT[5], TTLOUT[6], TTLOUT[7]],
    3: [TTLOUT[3]],
    4: [TTLOUT[8]],
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
    instrument=i22.BL,
    detectors=FAST_DETECTORS,
    instrument_session=DEFAULT_INSTRUMENT_SESSION,
)


# BlueAPI client
blueapi_config_path = f"./src/saxs_bluesky/blueapi_configs/{i22.BL}_blueapi_config.yaml"
CLIENT = BlueAPIPythonClient("i22", blueapi_config_path, DEFAULT_INSTRUMENT_SESSION)
