import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.devices.beamlines.b21.flame_spectrometer import FlameSpectrometer


def take_flame_data(
    filepath: str,
    filename: str,
    exposure_time_ms: int,
    flame: FlameSpectrometer = inject("flame_spectrometer"),
) -> MsgGenerator:
    yield from bps.mv(
        flame.filename,
        filename,
        flame.filepath,
        filepath,
        flame.exposure_time_ms,
        exposure_time_ms,
    )

    yield from bps.stage(flame)
    yield from bps.trigger(flame)
    yield from bps.unstage(flame)
