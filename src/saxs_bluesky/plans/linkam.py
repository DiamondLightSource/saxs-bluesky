import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.common.coordination import group_uuid
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    StandardDetector,
    StandardFlyer,
)
from ophyd_async.fastcs.panda import (
    HDFPanda,
    StaticSeqTableTriggerLogic,
)
from pydantic import validate_call
from scanspec.core import Path

# from scanspec.plot import plot_spec
from scanspec.specs import Line

from saxs_bluesky.stubs.panda_stubs import fly_and_collect_with_wait
from saxs_bluesky.utils.profile_groups import Group, Profile
from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

BL = get_saxs_beamline()
CONFIG = load_beamline_config()
DEFAULT_PANDA = CONFIG.DEFAULT_PANDA
FAST_DETECTORS = CONFIG.FAST_DETECTORS
DEFAULT_BASELINE = CONFIG.DEFAULT_BASELINE


@validate_call(config={"arbitrary_types_allowed": True})
def run_linkam(
    start: float | int,
    stop: float | int,
    num: int,
    rate: float | int,
    exposure: int,
    wait: float | int = 0,
    hold: float | int = 0,
    time_units: str = "MS",
    linkam: Linkam3 = inject("linkam3"),  # noqa
    detectors: list[StandardDetector] = FAST_DETECTORS,
    panda: HDFPanda = DEFAULT_PANDA,
) -> MsgGenerator:
    profile = Profile(repeats=num)
    profile.append_group(
        Group(
            frames=1,
            trigger="IMMEDIATE",
            wait_time=10,
            wait_units=time_units,
            run_time=exposure,
            run_units=time_units,
            wait_pulses=[0, 0, 0, 0],
            run_pulses=[1, 1, 1, 1],
        )
    )

    trigger_info = profile.return_trigger_info(0.1)
    panda_seq_table = panda.seq[CONFIG.DEFAULT_SEQ]
    trigger_logic = StaticSeqTableTriggerLogic(panda_seq_table)
    flyer = StandardFlyer(trigger_logic)
    all_devices = detectors + DEFAULT_BASELINE

    # STAGE SETS HDF WRITER TO ON
    yield from bps.stage_all(*all_devices, flyer, group="setup")
    # yield from stage_and_prepare_detectors(list(detectors), flyer, trigger_info)
    for det in detectors:
        ###this tells the detector how may triggers to expect and sets the CAN aquir
        yield from bps.prepare(det, trigger_info, wait=True, group="setup")
    yield from bps.wait(group="setup", timeout=DEFAULT_TIMEOUT * len(detectors))

    # Collect metadata
    plan_args = {
        "total_frames": trigger_info.number_of_events,
        "duration": trigger_info.livetime,
        "panda": panda.name + ":" + repr(panda),
        # "detectors": {device.name + ":" + repr(device) for device in detectors},
        # "baseline": {device.name + ":" + repr(device) for device in DEFAULT_BASELINE},
    }
    # Add panda to detectors so it captures and writes data.
    # It needs to be in metadata but not metadata planargs.
    _md = {
        "detectors": {device.name for device in detectors},
        "plan_args": plan_args,
        "hints": {},
    }

    yield from bps.mv(linkam, start)
    yield from bps.abs_set(linkam.ramp_rate, rate)

    spec = Line(linkam, start, stop, num)
    stack = spec.calculate()
    path = Path(stack)
    chunk = path.consume(num)

    print(chunk)
    print(chunk.duration)

    @bpp.baseline_decorator(DEFAULT_BASELINE)
    @bpp.run_decorator(md=_md)
    def run():
        linkam_group = group_uuid("linkam")

        yield from bps.abs_set(linkam.set_point, stop)

        yield from fly_and_collect_with_wait(
            stream_name="primary",
            detectors=list(detectors),
            flyer=flyer,
        )

        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)

    yield from run()

    # plot_spec(spec)
