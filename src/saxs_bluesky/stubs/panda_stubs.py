import bluesky.plan_stubs as bps
import numpy as np
from bluesky.utils import MsgGenerator, short_uid
from dodal.beamlines import module_name_for_beamline
from dodal.log import LOGGER
from dodal.utils import AnyDevice, make_all_devices, make_device
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    StandardDetector,
    StandardFlyer,
    YamlSettingsProvider,
    wait_for_value,
)
from ophyd_async.fastcs.panda import (
    HDFPanda,
    PandaBitMux,
    PcompInfo,
    SeqTableInfo,
)
from ophyd_async.plan_stubs import (
    apply_panda_settings,
    retrieve_settings,
    store_settings,
)


def return_connected_device(beamline: str, device_name: str):
    """
    Connect to a device on the specified beamline and return the connected device.

    Args:
        beamline (str): Name of the beamline.
        device_name (str): Name of the device to connect to.

    Returns:
        StandardDetector: The connected device.
    """

    module_name = module_name_for_beamline(beamline)

    devices = make_device(
        f"dodal.beamlines.{module_name}", device_name, connect_immediately=True
    )
    return devices[device_name]


def return_module_name(beamline: str) -> str:
    """
    Takes the name of a beamline, and returns the name of the Dodal module where all
    the devices for that module are stored
    """

    module_name = module_name_for_beamline(beamline)
    return f"dodal.beamlines.{module_name}"


def make_beamline_devices(beamline: str) -> dict[str, AnyDevice]:
    """
    Takes the name of a beamline and async creates all the devices for a beamline,
    whether they are connected or not.
    """

    module = return_module_name(beamline)
    beamline_devices, _ = make_all_devices(module)

    return beamline_devices


def fly_and_collect_with_wait(
    stream_name: str,
    flyer: StandardFlyer[SeqTableInfo] | StandardFlyer[PcompInfo],
    detectors: list[StandardDetector],
):
    """Kickoff, complete and collect with a flyer and multiple detectors and wait.

    This stub takes a flyer and one or more detectors that have been prepared. It
    declares a stream for the detectors, then kicks off the detectors and the flyer.
    The detectors are collected until the flyer and detectors have completed.

    see also from ophyd_async.plan_stubs import fly_and_collect

    """

    yield from bps.declare_stream(*detectors, name=stream_name, collect=True)
    yield from bps.kickoff(flyer, wait=True)
    for detector in detectors:
        yield from bps.kickoff(detector)

    # collect_while_completing
    group = short_uid(label="complete")

    yield from bps.complete(flyer, wait=False, group=group)
    for detector in detectors:
        yield from bps.complete(detector, wait=False, group=group)

    done = False
    while not done:
        try:
            yield from bps.wait(group=group, timeout=None)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            *detectors,
            return_payload=False,
            name=stream_name,
        )
    yield from bps.wait(group=group)
    yield from bps.sleep(2)


def load_settings_from_yaml(yaml_directory: str, yaml_file_name: str, panda: HDFPanda):
    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    return settings


def upload_yaml_to_panda(
    yaml_directory: str, yaml_file_name: str, panda: HDFPanda
) -> MsgGenerator:
    """

    Takes a folder of the directory where the yaml is saved, the name of the yaml file
    and the panda we want

    to apply the settings to, and uploaded the ophyd async settings pv yaml to the panda

    """

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    yield from apply_panda_settings(settings)


def save_device_to_yaml(
    yaml_directory: str, yaml_file_name: str, device
) -> MsgGenerator:
    """

    Takes a folder of the directory where the yaml will be saved,
    the name of the yaml file and the panda we want

    then saves the ophyd async pv yaml to the given path

    """

    provider = YamlSettingsProvider(yaml_directory)
    yield from store_settings(provider, yaml_file_name, device)


def return_max_deadtime(
    detectors: list[StandardDetector], exposure: float = 1.0
) -> float:
    """
    Given a list of connected detector devices, and an exposure time,
    it returns an array of the deadtime for each detector
    """

    deadtimes = (
        np.array([det._controller.get_deadtime(exposure) for det in detectors])  # noqa: SLF001
        + 2e5  # add small buffer
    )

    for det, dead in zip(detectors, deadtimes, strict=True):
        LOGGER.info(f"Deadtime is {dead.value} for {det.name}")

    max_deadtime = np.amax(deadtimes)

    return max_deadtime


def wait_until_complete(pv_obj, waiting_value=0, timeout=None):
    """
    An async wrapper for the ophyd async wait_for_value function,
    to allow it to run inside the bluesky run engine
    Typical use case is waiting for an active pv to change to 0,
    indicating that the run has finished, which then allows the
    run plan to disarm all the devices.
    """

    async def _wait():
        await wait_for_value(pv_obj, waiting_value, timeout=timeout)

    yield from bps.wait_for([_wait])


def set_panda_pulses(
    panda: HDFPanda,
    pulses: list[int],
    setting: str = "arm",
    group="arm_panda",
):
    """

    Takes a HDFPanda and a list of integers corresponding

    to the number of the pulse blocks.

    Iterates through the numbered pulse blocks

    and arms them and then waits for all to be armed.

    """

    if setting.lower() == "arm":
        value = PandaBitMux.ONE.value
    else:
        value = PandaBitMux.ONE.value

    for n_pulse in pulses:
        yield from bps.abs_set(
            panda.pulse[int(n_pulse)].enable,  # type: ignore
            value,
            group=group,
        )

    yield from bps.wait(group=group, timeout=DEFAULT_TIMEOUT)
