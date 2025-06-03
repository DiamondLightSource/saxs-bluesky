import os
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Annotated, List
import numpy as np
from importlib import import_module

from pydantic_core import from_json
from pydantic import validate_call #,NonNegativeFloat,


from bluesky.run_engine import RunEngine
from bluesky.utils import MsgGenerator
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from dodal.log import LOGGER
from dodal.utils import get_beamline_name
from dodal.common.visit import RemoteDirectoryServiceClient, StaticVisitPathProvider

from ophyd_async.core import (
    DetectorTrigger,
    StandardFlyer,
    TriggerInfo,
	wait_for_value,
	AsyncStatus, 
    StandardDetector)


from ophyd_async.fastcs.panda import (
    HDFPanda,
    SeqTableInfo,
    StaticSeqTableTriggerLogic)
#     PandaPcompDirection,
#     PcompInfo,
#     SeqTrigger,
#     SeqTable,
# )

from ophyd_async.plan_stubs import (ensure_connected,
                                    get_current_settings)


# from dodal.beamlines.i22 import saxs, waxs, i0, it, TetrammDetector, panda1
# from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator

from dodal.common import inject
from dodal.common.beamlines.beamline_utils import (
    get_path_provider,
    set_path_provider)

from ProfileGroups import (Profile,  
                           ProfileLoader) # Group

from stubs.PandAStubs import (return_connected_device,
								  make_beamline_devices,
                                  fly_and_collect_with_wait,
                                  load_settings_from_yaml,
                                  upload_yaml_to_panda)
								  
# from stubs.PandAStubs import save_device_to_yaml, return_module_name


BL = get_beamline_name(os.environ['BEAMLINE'])
BL_config = import_module(f"beamline_configs.{BL}_config")

DEADTIME_BUFFER = BL_config.DEADTIME_BUFFER
DEFAULT_SEQ = BL_config.DEFAULT_SEQ
GENERAL_TIMEOUT = BL_config.GENERAL_TIMEOUT
PULSEBLOCKS = BL_config.PULSEBLOCKS
CONFIG_NAME = BL_config.CONFIG_NAME


class PANDA(Enum):
    Enable = "ONE"
    Disable = "ZERO"



def wait_until_complete(pv_obj, waiting_value=0, timeout=None):
    """
    An async wrapper for the ophyd async wait_for_value function, to allow it to run inside the bluesky run engine
    Typical use case is waiting for an active pv to change to 0, indicating that the run has finished, which then allows the
    run plan to disarm all the devices.
    """

    async def _wait():
        await wait_for_value(pv_obj, waiting_value, timeout=timeout)

    yield from bps.wait_for([_wait])



def set_experiment_directory(beamline: str, visit_path: Path):
    """Updates the root folder"""

    print("should not require this to also be set in i22.py")

    set_path_provider(
    StaticVisitPathProvider(
        beamline,
        Path(visit_path),
        client=RemoteDirectoryServiceClient(f"http://{beamline}-control:8088/api"),
        )
    )

    suffix = datetime.now().strftime("_%Y%m%d%H%M%S")

    async def set_panda_dir():
        await get_path_provider().update(directory=visit_path, suffix=suffix)

    yield from bps.wait_for([set_panda_dir])



def modify_panda_seq_table(panda: HDFPanda, profile: Profile, n_seq=1):

    """
    
    Modifies the panda sequencer table, the default sequencer table to modify is the first one.

    Takes the panda and a Profile and then uses this to apply the sequencer table
    
    """

    seq_table = profile.seq_table()
    n_cycles = profile.cycles
    # time_unit = profile.best_time_unit
    
    group = "modify-seq"
    # yield from bps.stage(panda, group=group) ###maybe need this
    yield from bps.abs_set(panda.seq[int(n_seq)].table, seq_table, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].repeats, n_cycles, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].prescale, 1, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].prescale_units, 's', group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)


def set_pulses(panda: HDFPanda, n_pulse: int, pulse_step: int, frequency_multiplier: int, step_units="ms", width_unit="ms"):

    group = "modify-pulse"
    # yield from bps.abs_set(panda.pulse[int(n_pulse)].trig_edge, "Rising", group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].delay, 0, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].width, 1, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].width_units, width_unit, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].pulses, frequency_multiplier, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].step, pulse_step, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].step_units, step_units, group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def arm_panda_pulses(panda: HDFPanda, pulses: list = list(np.arange(PULSEBLOCKS)+1), n_seq=1, group="arm_panda"):

    """
    
    Takes a HDFPanda and a list of integers corresponding to the number of the pulse blocks.

    Iterates through the numbered pulse blocks and arms them and then waits for all to be armed.
    
    """

    # yield from wait_until_complete(panda.seq[n_seq].enable, PANDA.Enable.value)


    for n_pulse in pulses:
        yield from bps.abs_set(panda.pulse[int(n_pulse)].enable, PANDA.Enable.value, group=group)  # type: ignore

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def disarm_panda_pulses(panda: HDFPanda, pulses: list = list(np.arange(PULSEBLOCKS)+1), n_seq = 1, group="disarm_panda"):
    

    """
    
    Takes a HDFPanda and a list of integers corresponding to the number of the pulse blocks.

    Iterates through the numbered pulse blocks and disarms them and then waits for all to be disarmed.
    
    """


    for n_pulse in pulses:
        yield from bps.abs_set(panda.pulse[n_pulse].enable, PANDA.Disable.value, group=group)

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def start_sequencer(panda: HDFPanda, n_seq: int = 1, group="start"):


    """
    
    Takes an HDFPanda, the number of the sequencer block and sets the sequencer block to enable, waits for it to complete and then if

    conintuous is not True, it will wait for the sequnce to finish and disable the sequencer
    
    """

    yield from bps.abs_set(panda.seq[n_seq].enable, PANDA.Enable.value, group=group)  # type: ignore
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT) 
    yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, True) #even though the signal might be sent it may not actually have happened yet, so so until it's true before continuing



def disable_sequencer(panda: HDFPanda, n_seq: int = 1,  wait: bool = False, group="stop"):

    """
    
    Disables the HDFPanda sequencer block.

    Takes an HDF panda and the number fo the sequencer block
    
    """

    if wait:
        yield from wait_until_complete(panda.seq[n_seq].active, False) #wait for this value to be true

    yield from bps.abs_set(panda.seq[n_seq].enable, PANDA.Disable.value, group=group) 
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)




def stage_and_prepare_detectors(detectors: list, flyer: StandardFlyer, trigger_info: TriggerInfo, group="det_atm"):

    """
    
    Iterates through all of the detectors specified and prepares them.
    
    """

    yield from bps.stage_all(*detectors, flyer, group=group)

    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group=group) ###this tells the detector how may triggers to expect and sets the CAN aquire on

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def return_deadtime(detectors: list, exposure=1) -> np.ndarray:

    """
    Given a list of connected detector devices, and an exposure time, it returns an array of the deadtime for each detector
    """

    deadtime = np.array(list(det._controller.get_deadtime(exposure) for det in detectors)) + DEADTIME_BUFFER
    return deadtime



def set_panda_output(panda: HDFPanda, output_type: str, output: int, state: str, group="switch"):
    """
    Set a Panda output (TTL or LVDS) to a specified state (ON or OFF).

    Args:
        panda (HDFPanda): The Panda device.
        output_type (str): Type of output ("TTL" or "LVDS").
        output (int): Output number.
        state (str): Desired state ("ON" or "OFF").
        group (str): Bluesky group name.
    """
    state_value = PANDA.Enable.value if state.upper() == "ON" else PANDA.Disable.value
    output_attr = getattr(panda, f"{output_type.lower()}out")[int(output)]
    yield from bps.abs_set(output_attr.val, state_value, group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



@AsyncStatus.wrap
async def update_path():

    path_provider = get_path_provider()
    await path_provider.update()

    return path_provider


@AsyncStatus.wrap
async def return_run_number():

    path_provider = get_path_provider()
    run = await path_provider.data_session()

    return run

def generate_repeated_trigger_info(profile: Profile, max_deadtime: float, livetime: float, trigger = DetectorTrigger.CONSTANT_GATE):

    repeated_trigger_info = []

    n_triggers = [group.frames for group in profile.groups] #[3, 1, 1, 1, 1] or something
    n_cycles = profile.cycles


    for pulse_block, multiplier in enumerate(profile.multiplier):

        trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
                                trigger=trigger, 
                                deadtime=max_deadtime,
                                livetime=profile.duration,
                                multiplier=multiplier,
                                frame_timeout=None)

        repeated_trigger_info.append(trigger_info)

def prepare_pulses(panda: HDFPanda):
    """
    
    Takes a panda and prepares the pulses, this is the last thing to do before starting the run
    
    """

    group = "panda_pulses"
    for pulse in range(1, PULSEBLOCKS + 1):
        yield from bps.prepare(panda.pulse[pulse], group=group)

    # pulse_data = yield from bps.rd(panda.seq[DEFAULT_SEQ])
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)


def check_and_apply_panda_settings(panda: HDFPanda, panda_name: str) -> MsgGenerator:

    """
    
    Checks the settings currently on the PandA - if different they will be overwritten with the ones

    specified in the CONFIG_NAME 

    Settings may have changed due to Malcolm or someone chnaging things in EPICS which might prevent the plan from running

    This mitigates that
    
    """
    

    yaml_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls") #this is the directory where the yaml files are stored
    yaml_file_name = f"{BL}_{CONFIG_NAME}_{panda_name}"

    current_panda_settings = yield from get_current_settings(panda)
    yaml_settings = yield from load_settings_from_yaml(yaml_directory, yaml_file_name)

    if current_panda_settings.__dict__ != yaml_settings.__dict__:
        print("Current Panda settings do not match the yaml settings, loading yaml settings to panda")
        LOGGER.info("Current Panda settings do not match the yaml settings, loading yaml settings to panda")

        print(f"{yaml_file_name}.yaml has been uploaded to PandA")
        LOGGER.info(f"{yaml_file_name}.yaml has been uploaded to PandA")
        ######### make sure correct yaml is loaded
        yield from upload_yaml_to_panda(yaml_directory=yaml_directory,yaml_file_name=yaml_file_name,panda=panda)


def check_tetramm():
    """
    Checks if the tetramm is connected and returns the tetramm device.
    If the tetramm is not connected, it will raise an error.
    """

    try:
        tetramm = return_connected_device("i22", "tetramm")
        return tetramm
    except Exception as e:
        LOGGER.error(f"Tetramm not connected: {e}")
        raise

def inject_all(active_detector_names: List[StandardDetector]):

    """
    
    Injects all of the devices into the dodal common beamline devices, so that they can be used in the plans
    
    """

    active_detectors = tuple([inject(dev) for dev in active_detector_names])

    return active_detectors

def multiple_pulse_blocks():
    
    pass
    # for pulse in PULSEBLOCKS
    #   get the pulse block, find out what is attached to it
    #   set the multiplier and possibly duration accordingly
    #   for det in detectors_on_pulse_block:
    #       trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
    #                                   trigger=DetectorTrigger.CONSTANT_GATE, 
    #                                  deadtime=max_deadtime,
    #                                  multiplier=1,
    #                                 frame_timeout=None)

def show_deadtime(detector_deadtime, active_detector_names):

    """
    
    Takes two iterables, detetors deadtimes and detector names, and prints the deadtimes in the log

    """

    for dt, dn in zip(detector_deadtime, active_detector_names):
        print(f"deadtime for {dn} is {dt}")
        LOGGER.info(f"deadtime for {dn} is {dt}")



# @attach_data_session_metadata_decorator() #only enable if can't update the path provider, otherwise updates twice
@validate_call(config={"arbitrary_types_allowed": True})
def configure_panda_triggering(beamline: Annotated[str, "Name of the beamline to run the scan on eg. i22 or b21."], 
    experiment: Annotated[str, "Experiment name eg. cm12345. This will go into /dls/data/beamline/experiment"], 
    profile: Annotated[Profile | str, "Profile or json of a Profile containing the infomation required to setup the panda, triggers, times etc"], 
    active_detector_names: Annotated[list, "List of str of the detector names, eg. saxs, waxs, i0, it"] = ["saxs","waxs"], 
    run_immediately: bool = True,
    panda_name="panda1", 
    force_load=True) -> MsgGenerator[None]:


    """
    
    This plans configures the panda and the detectors, setting them up for hardware triggering, loads all of the correct

    settings and then may or may not run the flyscanning
    
    """

    if isinstance(profile, str):
        profile = Profile.model_validate(from_json(profile, allow_partial=True)) #convert from json to Profile object
    elif isinstance(profile, Profile):
        pass
    else: 
        raise TypeError("Profile must be a Profile object or a json string of a Profile object")


    visit_path = os.path.join(f"/dls/{beamline}/data",str(datetime.now().year), experiment) 
    
    LOGGER.info(f"Data will be saved in {visit_path}")
    print(f"Data will be saved in {visit_path}")

    yield from set_experiment_directory(beamline, visit_path)

    beamline_devices = make_beamline_devices(beamline) #this could be done faster with make_devices instead of make_all_devices
    panda = beamline_devices[panda_name]
    
    try:
        yield from ensure_connected(panda) #ensure the panda is connected
    except Exception as e:
        LOGGER.error(f"Failed to connect to PandA: {e}")
        raise

    ####################
    # v CHECK TO SEE IF THIS CAN BE PERFORMED IN A SMARTER WAY v


    try:
        active_detectors = inject_all(active_detector_names)
    except Exception as e:
        LOGGER.error(f"Failed to inject active detectors: {e}")
        active_detectors = tuple([beamline_devices[det_name] for det_name in active_detector_names]) ###must be a tuple to be hashable and therefore work with bps.stage_all or whatever
    ######################

    print("\n",active_detectors,"\n")
    LOGGER.info("\n",active_detectors,"\n")

    for device, device_name in zip(active_detectors, active_detector_names):
        try:
            yield from ensure_connected(device)
            print(f"{device_name} is connected")
        except Exception as e:
            LOGGER.error(f"{device} not connected: {e}")
            raise

    detector_deadtime = return_deadtime(detectors=active_detectors, exposure=profile.duration)
    max_deadtime = max(detector_deadtime)
    # show_deadtime(detector_deadtime, max_deadtime)

    #load Panda setting to panda
    if force_load is True:
        yield from check_and_apply_panda_settings(panda, panda_name)

    active_pulses = profile.active_out+1 #because python counts from 0, but panda counts from 1
    n_cycles = profile.cycles
    seq_table = profile.seq_table() #seq table should be grabbed from the panda and used instead, in order to decouple run from setup panda
    n_triggers = [group.frames for group in profile.groups] #[3, 1, 1, 1, 1] or something
    duration = profile.duration

    ############################################################
    # ###setup triggering of detectors
    table_info = SeqTableInfo(sequence_table=seq_table, repeats=n_cycles)


    #set up trigger info etc
    trigger_info = TriggerInfo(number_of_events = n_triggers*n_cycles, 
                            trigger=DetectorTrigger.CONSTANT_GATE, # or maybe EDGE_TRIGGER
                            deadtime=max_deadtime,
                            livetime=np.amax(profile.duration_per_cycle),
                            exposures_per_event=1,
                            frame_timeout=duration)
    

    ############################################################

    trigger_logic = StaticSeqTableTriggerLogic(panda.seq[DEFAULT_SEQ]) #flyer and prepare fly, sets the sequencers table
    flyer = StandardFlyer(trigger_logic) #flyer and prepare fly, sets the sequencers table

    # ####stage the detectors, the flyer, the panda
    yield from bps.prepare(flyer, table_info, wait=True) #setup triggering on panda - changes the sequence table - wait otherwise risking _context missing error
    yield from stage_and_prepare_detectors(active_detectors, flyer, trigger_info) ###change the sequence table
    # ###### ^ this is the last thing setting up the panda

    if run_immediately:
        yield from run_panda_triggering(panda, active_detectors, active_pulses)


@bpp.run_decorator() #    # open/close run
@validate_call(config={"arbitrary_types_allowed": True})
def run_panda_triggering(panda: HDFPanda, active_detectors, active_pulses, group="run") -> MsgGenerator[None]:


    """
    
    This will run whatever flyscanning settings are currenly loaded on the PandA and start it triggering
    
    """
    
    trigger_logic = StaticSeqTableTriggerLogic(panda.seq[DEFAULT_SEQ]) #flyer and prepare fly, sets the sequencers table
    flyer = StandardFlyer(trigger_logic) #flyer and prepare fly, sets the sequencers table

    ##########################
    #arm the panda pulses
    yield from arm_panda_pulses(panda=panda, pulses=active_pulses)

    ###########################
    yield from fly_and_collect_with_wait(
        stream_name='primary',
        detectors=active_detectors,
        flyer=flyer,
    )
    ##########################
    ###########################
    ####start diabling and unstaging everything
    yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, False)
    yield from disarm_panda_pulses(panda=panda, pulses=active_pulses) #start set to false because currently don't actually want to collect data
    yield from bps.unstage_all(*active_detectors, flyer)  #stops the hdf capture mode




if __name__ == "__main__":

    RE = RunEngine(call_returns_result=True) 

    #################################

    #notes to self
    # tetramm only works with mulitple triggers, something to do with arm_status being set to none possible.
    #when tetramm has multiple triggers eg, 2 the data shape is not 2. only every 1. It's duration is twice as long, but still 1000 samples

    #tetramm.py
    # async def prepare(self, trigger_info: TriggerInfo):
    #     self.maximum_readings_per_frame = self.maximum_readings_per_frame*sum(trigger_info.number_of_events)

    #still getting the experiment number jumping by two
    #neeed to sort out pulses on panda
    #split setup and run 


    ###if TETRAMMS ARE NOT WORKING TRY TfgAcquisition() in gda to reset all malcolm stuff to defaults


    ###################################
    # Profile(id=0, cycles=1, in_trigger='IMMEDIATE', out_trigger='TTLOUT1', groups=[Group(id=0, frames=1, wait_time=100, wait_units='ms', run_time=100, run_units='ms', wait_pause=False, run_pause=False, wait_pulses=[1, 0, 0, 0, 0, 0, 0, 0], run_pulses=[0, 0, 0, 0, 0, 0, 0, 0])], multiplier=[1, 2, 4, 8, 16])

    default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"profile_yamls","panda_config.yaml")
    configuration = ProfileLoader.read_from_yaml(default_config_path)
    profile = configuration.profiles[1]
    # RE(setup_panda("i22", "cm40643-3/bluesky", profile, active_detector_names=["saxs", "waxs", "i0", "it"], force_load=False))

    # for i in range(20):

    RE(configure_panda_triggering("i22", "cm40643-3/bluesky", profile, active_detector_names=["saxs", "waxs", "i0", "it"], force_load=False))

    # profile = configuration.profiles[2]
    # RE(setup_panda("i22"None, "cm40643-3/bluesky", profile, active_detector_names=["saxs", "i0"], force_load=False))

    # RE(panda_triggers_detectors("i22", active_detector_names=["saxs", "i0"]))


    # dev_name = "panda1"
    # connected_dev = return_connected_device('i22',dev_name)
    # print(f"{connected_dev=}")
    # RE(save_device_to_yaml(yaml_directory= os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls"), yaml_file_name=f"{dev_name}_pv_without_pulse", device=connected_dev))



