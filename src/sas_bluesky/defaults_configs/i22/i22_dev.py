from dodal.common import inject
from ophyd_async.core import StandardDetector
from ophyd_async.fastcs.panda import HDFPanda

FAST_DETECTORS: set[StandardDetector] = {
    inject("saxs"),
    inject("waxs"),
    inject("i0"),
    inject("it"),
}


DEFAULT_PANDA: HDFPanda = inject("panda1")
