import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator, short_uid
from dodal.beamlines import module_name_for_beamline
from dodal.log import LOGGER
from dodal.utils import AnyDevice, make_all_devices, make_device
from ophyd_async.core import (
    StandardDetector,
    StandardFlyer,
    YamlSettingsProvider,
    wait_for_value,
)
from ophyd_async.fastcs.panda import HDFPanda, PcompInfo, SeqTableInfo
from ophyd_async.plan_stubs import (
    apply_panda_settings,
    apply_settings_if_different,
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
    yield from bps.sleep(1)


def get_settings_dir_and_name(
    beamline: str, settings_name: str, panda_name: str
) -> tuple:
    yaml_directory = os.path.join(
        os.path.dirname(Path(__file__).parent), "ophyd_panda_yamls"
    )
    yaml_file_name = f"{beamline}_{settings_name}_{panda_name}"

    return yaml_directory, yaml_file_name


def check_and_apply_panda_settings(
    panda: HDFPanda, beamline: str, settings_name: str, panda_name: str
) -> MsgGenerator:
    """

    Takes a folder of the directory where the yaml is saved, the name of the yaml file
    and the panda we want

    to apply the settings to, and uploaded the ophyd async settings pv yaml to the panda

    """

    yaml_directory, yaml_file_name = get_settings_dir_and_name(
        beamline=beamline, settings_name=settings_name, panda_name=panda_name
    )

    yield from load_settings_to_panda(yaml_directory, yaml_file_name, panda)


def load_settings_to_panda(
    yaml_directory: str, yaml_file_name: str, panda: HDFPanda
) -> MsgGenerator:
    """
    load settings to panda if different
    """

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    yield from apply_settings_if_different(settings, apply_panda_settings)


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


def log_deadtime(
    active_detector_names: Iterable[Any], detector_deadtime: Iterable[Any]
):
    """

    Takes two iterables, detetors deadtimes and detector names,
    and prints the deadtimes in the log

    """

    for dt, dn in zip(detector_deadtime, active_detector_names, strict=True):
        LOGGER.info(f"deadtime for {dn} is {dt}")


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
