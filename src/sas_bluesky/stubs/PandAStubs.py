from bluesky.utils import MsgGenerator, short_uid
import bluesky.plan_stubs as bps


from ophyd_async.core import (
    StandardDetector,
    StandardFlyer,
    YamlSettingsProvider)


from ophyd_async.plan_stubs._wait_for_awaitable import wait_for_awaitable
from ophyd_async.plan_stubs import (apply_panda_settings, 
									retrieve_settings, 
									store_settings)

from ophyd_async.fastcs.panda import (
    HDFPanda,
    SeqTableInfo,
    PcompInfo
)

from dodal.beamlines import module_name_for_beamline
from dodal.utils import make_device, make_all_devices

from dodal.devices.oav.oav_detector import OAV
from dodal.devices.oav.oav_parameters import OAVParameters
from dodal.devices.areadetector.plugins.CAM import ColorMode




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
    devices = make_device(f"dodal.beamlines.{module_name}", device_name, connect_immediately=True)
    return devices[device_name]


def return_module_name(beamline: str) -> str:
    """
    Takes the name of a beamline, and returns the name of the Dodal module where all the devices for that module are stored
    """
    
    module_name = module_name_for_beamline(beamline)
    return f"dodal.beamlines.{module_name}"


def make_beamline_devices(beamline: str) -> list:
    
    """
    Takes the name of a beamline and async creates all the devices for a beamline, whether they are connected or not. 
    """

    module = return_module_name(beamline)
    beamline_devices = make_all_devices(module)[0]

    return beamline_devices


def fly_and_collect_with_wait(
    stream_name: str,
    flyer: StandardFlyer[SeqTableInfo] | StandardFlyer[PcompInfo],
    detectors: list[StandardDetector],
):
    """Kickoff, complete and collect with a flyer and multiple detectors and wait breifly.

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
            yield from bps.wait(group=group, timeout=1)
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
    

def load_settings_from_yaml(yaml_directory: str, yaml_file_name: str):

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from wait_for_awaitable(provider.retrieve(yaml_file_name))

    return settings

def upload_yaml_to_panda(yaml_directory: str, yaml_file_name: str, panda: HDFPanda) -> MsgGenerator:

    """
    
    Takes a folder of the directory where the yaml is saved, the name of the yaml file and the panda we want 

    to apply the settings to, and uploaded the ophyd async settings pv yaml to the panda
    
    """

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    yield from apply_panda_settings(settings)
	

def save_device_to_yaml(yaml_directory: str, yaml_file_name: str, device) -> MsgGenerator:

    """
    
    Takes a folder of the directory where the yaml will be saved, the name of the yaml file and the panda we want 

    then saves the ophyd async pv yaml to the given path
    
    """

    provider = YamlSettingsProvider(yaml_directory)
    yield from store_settings(provider, yaml_file_name, device)
    

def setup_oav(oav: OAV,  parameters: OAVParameters, group="oav_setup"):

    yield from bps.abs_set(oav.cam.color_mode, ColorMode.RGB1, group=group)
    yield from bps.abs_set(oav.cam.acquire_period, parameters.acquire_period, group=group)
    yield from bps.abs_set(oav.cam.acquire_time, parameters.exposure, group=group)
    yield from bps.abs_set(oav.cam.gain, parameters.gain, group=group)