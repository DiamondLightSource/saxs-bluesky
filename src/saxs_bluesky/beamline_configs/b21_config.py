import os
from copy import deepcopy

from dodal.beamlines import b21
from dodal.common import inject
from ophyd_async.core import StandardDetector, StandardReadable
from ophyd_async.fastcs.panda import HDFPanda

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

BL = b21.BL


"""

Configuration for b21 PandA beamline

"""

DEFAULT_INSTRUMENT_SESSION = "cm40642-5"

###THESE NEED TO BE LISTS TO BE SERIALISED
FAST_DETECTORS: list[StandardDetector] = [inject("saxs"), inject("waxs")]

DEFAULT_PANDA: HDFPanda = inject("panda1")

DEFAULT_BASELINE: list[StandardReadable] = [
    inject("slits_1"),
    inject("slits_2"),
    inject("slits_3"),
    inject("slits_5"),
    inject("slits_6"),
    inject("synchrotron"),
    inject("it"),
]


# GUI Elements
PULSEBLOCKS = 6  # this is higher than the number of pulseblocks
# so each connection cant have a pulseblock for mutpliers
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["fs", "saxs/waxs", "led1", "led2", "led3", "led4"]

# PandA Wiring connections

TTLIN = {1: "Beamstop V2F", 2: None, 3: None, 4: "TFG WAXS", 5: "TFG FS", 6: "TFG SAXS"}

TTLOUT = {
    1: "fs",
    2: "saxs",
    3: "waxs",
    4: "led1",
    5: "led2",
    6: "led3",
    7: "led4",
    8: None,
    9: None,
    10: "v2f relay",
}


LVDSIN = {1: None, 2: None}


LVDSOUT = {1: "saxs", 2: "waxs"}

PULSE_CONNECTIONS = {
    1: [TTLOUT[1]],
    2: [TTLOUT[2], LVDSOUT[2]],
    3: [TTLOUT[4]],
    4: [TTLOUT[5]],
    5: [TTLOUT[6]],
    6: [TTLOUT[7]],
}


"""

# Panda plan parameters

"""

# Buffer added to deadtime to handle minor discrepencies between detector
# and panda clocks
DEADTIME_BUFFER = 20e-6
# default sequencer is this one, b21 currently uses seq 1 for somthing else
DEFAULT_SEQ = 2

CONFIG_NAME = "PandaTriggerWithCounterAndPCAP"


"""

# DEFAULT PROFILES

"""

DEFAULT_GROUP = Group(
    frames=1,
    trigger="IMMEDIATE",
    wait_time=1,
    wait_units="S",
    run_time=1,
    run_units="S",
    wait_pulses=[1, 0, 0, 0, 0, 0],
    run_pulses=[1, 1, 0, 0, 0, 0],
)


DEFAULT_PROFILE = Profile(
    repeats=1,
    groups=[deepcopy(DEFAULT_GROUP)],
    multiplier=None,
)

DEFAULT_EXPERIMENT = ExperimentLoader(
    profiles=[deepcopy(DEFAULT_PROFILE)],
    instrument=b21.BL,
    detectors=FAST_DETECTORS,
    instrument_session=DEFAULT_INSTRUMENT_SESSION,
)


blueapi_config_path = (
    f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"
)
CLIENT = BlueAPIPythonClient(BL, blueapi_config_path, DEFAULT_INSTRUMENT_SESSION)
