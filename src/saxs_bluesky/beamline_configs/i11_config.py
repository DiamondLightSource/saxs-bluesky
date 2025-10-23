import os
from copy import deepcopy

from dodal.beamlines import i11
from dodal.common import inject
from ophyd_async.core import StandardDetector, StandardReadable
from ophyd_async.fastcs.panda import HDFPanda

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import ExperimentLoader, Group, Profile

BL = i11.BL


"""

Configuration for b21 PandA beamline

"""

DEFAULT_INSTRUMENT_SESSION = "cm40625-4"

###THESE NEED TO BE LISTS TO BE SERIALISED
FAST_DETECTORS: list[StandardDetector] = [inject("mythen")]

DEFAULT_PANDA: HDFPanda = inject("panda1")

DEFAULT_BASELINE: list[StandardReadable] = [
    inject("slits_1"),
    inject("slits_2"),
    inject("slits_3"),
    inject("slits_5"),
    inject("slits_6"),
    inject("synchrotron"),
]


# GUI Elements
PULSEBLOCKS = 4  # this is higher than the number of pulseblocks
# so each connection cant have a pulseblock for mutpliers
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["mythen", "None", "None", "None"]

# PandA Wiring connections

TTLIN = {1: "Beamstop V2F", 2: None, 3: None, 4: "TFG WAXS", 5: "TFG FS", 6: "TFG SAXS"}

TTLOUT = {
    1: "mythen",
    2: None,
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

# Panda plan parameters

"""

# Buffer added to deadtime to handle minor discrepencies between detector
# and panda clocks
DEADTIME_BUFFER = 20e-6
# default sequencer is this one, b21 currently uses seq 1 for somthing else
DEFAULT_SEQ = 2

CONFIG_NAME = "PandaTrigge"


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
    wait_pulses=[1, 0, 0, 0],
    run_pulses=[1, 1, 0, 0],
)


DEFAULT_PROFILE = Profile(
    repeats=1,
    seq_trigger="IMMEDIATE",
    groups=[deepcopy(DEFAULT_GROUP)],
    multiplier=[1, 1, 1, 1],
)

DEFAULT_EXPERIMENT = ExperimentLoader(
    profiles=[deepcopy(DEFAULT_PROFILE)],
    instrument=i11.BL,
    detectors=FAST_DETECTORS,
    instrument_session=DEFAULT_INSTRUMENT_SESSION,
)


blueapi_config_path = (
    f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"
)
CLIENT = BlueAPIPythonClient(BL, blueapi_config_path, DEFAULT_INSTRUMENT_SESSION)
