import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.devices.motors import Motor
from dodal.log import LOGGER
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from dodal.plans import scanspec
from ophyd_async.core import (
    StandardReadable,
)
from pydantic import validate_call
from scanspec.core import Path
from scanspec.specs import Line

from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

BL = get_saxs_beamline()
CONFIG = load_beamline_config()
DEFAULT_PANDA = CONFIG.DEFAULT_PANDA
FAST_DETECTORS = CONFIG.FAST_DETECTORS
DEFAULT_BASELINE = CONFIG.DEFAULT_BASELINE


@bpp.run_decorator()  #    # open/close run
@bpp.baseline_decorator(DEFAULT_BASELINE)
@attach_data_session_metadata_decorator()
def step_mapping() -> MsgGenerator:
    yield from bps.null()


@validate_call(config={"arbitrary_types_allowed": True})
def twod_grid_map(detectors: list[StandardReadable], axes: list[Motor]):
    grid = Line(inject("base.y"), 2.1, 3.8, 12) * ~Line(inject("base.x"), 0.5, 1.5, 10)
    # spec = Fly(0.4 @ grid) & Circle("x", "y", 1.0, 2.8, radius=0.5)
    stack = grid.calculate()

    # path = Path(stack, start=5, num=30)
    stack[0].axes()  # ['y', 'x']

    path = Path(stack, start=5, num=30)
    chunk = path.consume(4096)  # you can't have any more than 4096 lines on a PandA

    LOGGER.info(len(stack[0]))  # 44
    LOGGER.info(chunk.midpoints)  # {'x': <ndarray len=10>, 'y': <ndarray len=10>}
    LOGGER.info(chunk.upper)  # bounds are same dimensionality as positions
    LOGGER.info(chunk.duration)  # duration of each frame

    yield from scanspec.spec_scan(set(detectors), grid)


if __name__ == "__main__":
    pass
