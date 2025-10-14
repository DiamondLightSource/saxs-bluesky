import os
from pathlib import Path
from typing import Annotated, Any

import bluesky.plan_stubs as bps
import bluesky.plans as bsp
import bluesky.preprocessors as bpp
import numpy as np
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.devices.motors import Motor
from dodal.log import LOGGER
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    StandardReadable,
    TriggerInfo,
    wait_for_value,
)
from ophyd_async.fastcs.panda import (
    HDFPanda,
    PandaBitMux,
    SeqTableInfo,
    StaticSeqTableTriggerLogic,
)
from ophyd_async.plan_stubs import ensure_connected, get_current_settings
from pydantic import validate_call

from saxs_bluesky.stubs.panda_stubs import (
    fly_and_collect_with_wait,
    load_settings_from_yaml,
    upload_yaml_to_panda,
)
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


STORED_DETECTORS: list[StandardDetector] | list[str] | None = None
STORED_PROFILE: Profile | None = None
STORED_TRIGGER_INFO: TriggerInfo | None = None

LOGGER.info(f"saxs bluesky is using the beamline: {BL}")


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


def stage_and_prepare_detectors(
    detectors: list[StandardDetector],
    flyer: StandardFlyer,
    trigger_info: TriggerInfo,
    group="det_atm",
):
    """

    Iterates through all of the detectors specified and prepares them.

    """

    yield from bps.stage_all(*detectors, flyer, group=group)

    for det in detectors:
        ###this tells the detector how may triggers to expect and sets the CAN aquire on
        yield from bps.prepare(det, trigger_info, wait=False, group=group)

    yield from bps.wait(group=group, timeout=DEFAULT_TIMEOUT)


def return_deadtime(
    detectors: list[StandardDetector], exposure: float = 1.0
) -> np.ndarray:
    """
    Given a list of connected detector devices, and an exposure time,
    it returns an array of the deadtime for each detector
    """

    deadtime = (
        np.array([det._controller.get_deadtime(exposure) for det in detectors])  # noqa: SLF001
        + CONFIG.DEADTIME_BUFFER
    )
    return deadtime


def generate_repeated_trigger_info(
    profile: Profile,
    max_deadtime: float,
    livetime: float,
    trigger=DetectorTrigger.CONSTANT_GATE,
) -> list[TriggerInfo]:
    repeated_trigger_info = []

    # [3, 1, 1, 1, 1] or something
    n_triggers = [group.frames for group in profile.groups]
    repeats = profile.repeats

    if profile.multiplier is not None:
        for multiplier in profile.multiplier:
            trigger_info = TriggerInfo(
                number_of_events=n_triggers * repeats,
                trigger=trigger,
                deadtime=max_deadtime,
                livetime=profile.duration,
                exposures_per_event=multiplier,
                exposure_timeout=None,
            )

            repeated_trigger_info.append(trigger_info)

    return repeated_trigger_info


def check_and_apply_panda_settings(panda: HDFPanda, panda_name: str) -> MsgGenerator:
    """

    Checks the settings currently on the PandA

    - if different they will be overwritten with the ones

    specified in the CONFIG.CONFIG_NAME

    Settings may have changed due to Malcolm or

    someone chnaging things in EPICS which might prevent the plan from running

    This mitigates that

    """

    # this is the directory where the yaml files are stored
    yaml_directory = os.path.join(
        os.path.dirname(Path(__file__).parent), "ophyd_panda_yamls"
    )
    yaml_file_name = f"{BL}_{CONFIG.CONFIG_NAME}_{panda_name}"

    current_panda_settings = yield from get_current_settings(panda)
    yaml_settings = yield from load_settings_from_yaml(yaml_directory, yaml_file_name)

    if current_panda_settings != yaml_settings:
        print(
            (
                "Current Panda settings do not match the yaml settings, ",
                "loading yaml settings to panda",
            )
        )
        LOGGER.info(
            (
                "Current Panda settings do not match the yaml settings, ",
                "loading yaml settings to panda",
            )
        )

        print(f"{yaml_file_name}.yaml has been uploaded to PandA")
        LOGGER.info(f"{yaml_file_name}.yaml has been uploaded to PandA")
        ######### make sure correct yaml is loaded
        yield from upload_yaml_to_panda(
            yaml_directory=yaml_directory, yaml_file_name=yaml_file_name, panda=panda
        )


def multiple_pulse_blocks():
    pass
    # for pulse in CONFIG.PULSEBLOCKS
    #   get the pulse block, find out what is attached to it
    #   set the multiplier and possibly duration accordingly
    #   for det in detectors_on_pulse_block:
    #       trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_repeats,
    #                                   trigger=DetectorTrigger.CONSTANT_GATE,
    #                                  deadtime=max_deadtime,
    #                                  multiplier=1,
    #                                 frame_timeout=None)


def show_deadtime(detector_deadtime, active_detector_names):
    """

    Takes two iterables, detetors deadtimes and detector names,
    and prints the deadtimes in the log

    """

    for dt, dn in zip(detector_deadtime, active_detector_names, strict=True):
        LOGGER.info(f"deadtime for {dn} is {dt}")


def set_panda_output(
    output_type: str = "TTL",
    output: int = 1,
    state: bool | int = 1,
    panda: HDFPanda = DEFAULT_PANDA,
    group: str = "switch",
) -> MsgGenerator:
    """
    Set a Panda output (TTL or LVDS) to a specified state (ON or OFF).

    Args:
        panda (HDFPanda): The Panda device.
        output_type (str): Type of output ("TTL" or "LVDS").
        output (int): Output number.
        state (str): Desired state ("ON" or "OFF").
        group (str): Bluesky group name.
    """
    state_value = PandaBitMux.ONE.value if state else PandaBitMux.ZERO.value
    output_attr = getattr(panda, f"{output_type.lower()}out")[int(output)]
    yield from bps.abs_set(output_attr.val, state_value, group=group)
    yield from bps.wait(group=group, timeout=DEFAULT_TIMEOUT)


def get_output(device: str) -> tuple[str | None, int | None]:
    device = device.upper()

    output_type = None
    output = None

    for out in CONFIG.TTLOUT.keys():
        if device == CONFIG.TTLOUT[out].upper():
            output_type = "TTL"
            output = out

    for out in CONFIG.CONFIG.LVDSOUT.keys():
        if device == CONFIG.TTLOUT[out].upper():
            output_type = "TTL"
            output = out

    return output_type, output


@validate_call(config={"arbitrary_types_allowed": True})
def turn_on(device: str) -> MsgGenerator:
    output_type, output = get_output(device)

    if (output_type is None) or (output is None):
        yield from bps.null()
        LOGGER.info("No detector of that name in beamline config")
    else:
        yield from set_panda_output(output_type, output, 1)


@validate_call(config={"arbitrary_types_allowed": True})
def turn_off(device: str) -> MsgGenerator:
    output_type, output = get_output(device)

    if (output_type is None) or (output is None):
        LOGGER.info("No detector of that name in beamline config")
        yield from bps.null()
    else:
        yield from set_panda_output(output_type, output, 0)


# @attach_data_session_metadata_decorator()
@validate_call(config={"arbitrary_types_allowed": True})
def configure_panda_triggering(
    profile: Annotated[
        Profile,
        (
            "Profile or json of a Profile containing the infomation required to setup ",
            "the panda, triggers, times etc",
        ),
    ],
    detectors: Annotated[
        list[StandardDetector],
        "List of str of the detector names, eg. saxs, waxs, i0, it",
    ] = FAST_DETECTORS,
    panda: HDFPanda = DEFAULT_PANDA,
    force_load: bool = False,
) -> MsgGenerator:
    """

    This plans configures the panda and the detectors,

    setting them up for hardware triggering, loads all of the correct

    settings.

    Stage - sets the hdf writer
    Prepare - sets the trigger info

    Stage must come before prepare

    """

    try:
        yield from ensure_connected(panda)  # ensure the panda is connected
    except Exception as e:
        LOGGER.error(f"Failed to connect to PandA: {e}")
        raise

    LOGGER.info("Using the following detectors:")
    LOGGER.info("")
    for det in detectors:
        LOGGER.info(str(det))

    detector_deadtime = return_deadtime(
        detectors=list(detectors), exposure=profile.duration
    )

    max_deadtime = max(detector_deadtime)
    # show_deadtime(detector_deadtime, max_deadtime)

    # load Panda setting to panda
    if force_load:
        yield from check_and_apply_panda_settings(panda, panda.name)

    # n_repeats = profile.repeats
    # seq table should be grabbed from the panda and used instead,
    # in order to decouple run from setup panda
    # seq_table = profile.seq_table

    if profile.multiplier is not None:
        LOGGER.info(f"Pulses used: {profile.active_pulses}")
        # arm the panda pulses if the profile has multipliers
        yield from set_panda_pulses(
            panda=panda, pulses=profile.active_pulses, setting="arm"
        )
        LOGGER.info(f"Multipliers values: {profile.multiplier}")

    ############################################################
    # setup triggering of detectors
    seq_table_info: SeqTableInfo = profile.seq_table_info

    # set up trigger info etc
    trigger_info: TriggerInfo = profile.return_trigger_info(max_deadtime)

    ############################################################
    # flyer and prepare fly, sets the sequencers table
    trigger_logic = StaticSeqTableTriggerLogic(panda.seq[CONFIG.DEFAULT_SEQ])
    flyer = StandardFlyer(trigger_logic)

    # setup triggering on panda - changes the sequence table
    # !! wait otherwise risking _context missing error
    # change the sequence table
    yield from bps.prepare(flyer, seq_table_info, wait=True)

    yield from set_detectors(detectors=detectors)  # store the detectors globally
    yield from set_profile(profile=profile)  # store the profile globally
    yield from set_trigger_info(trigger_info=trigger_info)  # store the profile globally


@attach_data_session_metadata_decorator()
@validate_call(config={"arbitrary_types_allowed": True})
def run_panda_triggering(
    panda: HDFPanda = DEFAULT_PANDA,
    baseline: list[StandardReadable] = DEFAULT_BASELINE,
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    """

    This will run whatever flyscanning settings
    are currenly loaded on the PandA and start it triggering

    """

    if STORED_TRIGGER_INFO is None:
        raise ValueError("No trigger info has been set, use set_trigger_info")
    else:
        trigger_info: TriggerInfo = STORED_TRIGGER_INFO  # type: ignore

    if STORED_DETECTORS is None:
        raise ValueError("No detectors have been set, use set_detectors")
    else:
        detectors: list[StandardDetector] = STORED_DETECTORS  # type: ignore

    # get the loaded seq table
    panda_seq_table = panda.seq[CONFIG.DEFAULT_SEQ]
    # flyer and prepare fly, sets the sequencers table
    trigger_logic = StaticSeqTableTriggerLogic(panda_seq_table)
    flyer = StandardFlyer(trigger_logic)

    # detectors = detectors + [panda]  # panda must be added so we can get HDF
    all_devices = detectors + DEFAULT_BASELINE

    # STAGE SETS HDF WRITER TO ON
    yield from bps.stage_all(*all_devices, flyer, group="setup")

    # yield from stage_and_prepare_detectors(list(detectors), flyer, trigger_info)
    for det in detectors:
        ###this tells the detector how may triggers to expect and sets the CAN aquir
        yield from bps.prepare(det, trigger_info, wait=True, group="setup")

    yield from bps.wait(group="setup", timeout=DEFAULT_TIMEOUT * len(detectors))

    ######################

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
    _md.update(metadata or {})

    ##################

    @bpp.baseline_decorator(baseline)
    @bpp.run_decorator(md=_md)
    def run():
        yield from fly_and_collect_with_wait(
            stream_name="primary",
            detectors=list(detectors),
            flyer=flyer,
        )

    yield from run()

    # name = "run"
    # yield from bps.declare_stream(*detectors, name=name, collect=True)
    # yield from bps.kickoff(flyer, wait=True)
    # for detector in detectors:
    #     yield from bps.kickoff(detector)
    # yield from bps.collect_while_completing([flyer], detectors, stream_name=name)

    ##########################
    ###########################
    yield from wait_until_complete(panda_seq_table.active, False)

    # turn off all pulses whether or not using
    yield from set_panda_pulses(
        panda=panda, pulses=list(np.array(range(4)) + 1), setting="disarm"
    )

    # start diabling and unstaging everything
    yield from bps.unstage_all(*all_devices, flyer)  # stops the hdf capture mode


def configure_and_run_panda_triggering(
    profile: Annotated[
        Profile,
        (
            "Profile or json of a Profile containing the infomation required to setup ",
            "the panda, triggers, times etc",
        ),
    ],
    detectors: Annotated[
        list[StandardDetector],
        "List of str of the detector names, eg. saxs, waxs, i0, it",
    ] = FAST_DETECTORS,
    panda: HDFPanda = DEFAULT_PANDA,
    force_load: bool = True,
) -> MsgGenerator:
    """

    This plans configures the panda and the detectors,

    setting them up for hardware triggering, loads all of the correct

    settings and then runs the flyscanning

    """

    yield from configure_panda_triggering(
        profile=profile,
        detectors=detectors,
        panda=panda,
        force_load=force_load,
    )

    # yield from run_panda_triggering(profile,
    # detectors=detectors, panda=panda)  # type: ignore


@validate_call(config={"arbitrary_types_allowed": True})
def set_detectors(
    detectors: list[str] | list[StandardDetector],
) -> MsgGenerator:
    global STORED_DETECTORS

    if isinstance(detectors[0], StandardDetector):
        STORED_DETECTORS = detectors
    else:
        STORED_DETECTORS = [inject(f) for f in detectors]  # type: ignore

    yield from bps.null()


@validate_call(config={"arbitrary_types_allowed": True})
def log_detectors() -> MsgGenerator:
    """
    Log the currently stored detectors using the configured logger.

    Yields:
        Msg: Bluesky message indicating detectors have been logged.
    """
    LOGGER.info(STORED_DETECTORS)
    yield from bps.null()


@validate_call(config={"arbitrary_types_allowed": True})
def set_profile(profile: Profile) -> MsgGenerator:
    """
    Store the provided profile globally for later use.

    Args:
        profile (Profile): The profile to store.
    Yields:
        Msg: Bluesky message indicating profile has been logged.
    """
    global STORED_PROFILE
    STORED_PROFILE = profile
    yield from bps.null()


@validate_call(config={"arbitrary_types_allowed": True})
def set_trigger_info(trigger_info: TriggerInfo) -> MsgGenerator:
    """
    Store the provided trigger info globally for later use.

    Args:
        trigger_info (TriggerInfo): The trigger info to store.
    Yields:
        Msg: Bluesky message indicating trigger info has been set.
    """
    global STORED_TRIGGER_INFO
    STORED_TRIGGER_INFO = trigger_info
    yield from bps.null()


def get_trigger_info() -> TriggerInfo | None:
    """
    Retrieve the globally stored trigger info.

    Returns:
        TriggerInfo | None: The stored trigger info, or None if not set.
    """
    return STORED_TRIGGER_INFO


def get_profile() -> Profile | None:
    """
    Retrieve the globally stored profile.

    Returns:
        Profile | None: The stored profile, or None if not set.
    """
    return STORED_PROFILE


@validate_call(config={"arbitrary_types_allowed": True})
def create_profile(
    repeats: int = 1,
    seq_trigger: str = "Immediate",
    multiplier: list[int] | None = None,
) -> MsgGenerator:
    global STORED_PROFILE

    STORED_PROFILE = Profile(
        repeats=repeats, seq_trigger=seq_trigger, multiplier=multiplier
    )

    yield from bps.null()


def append_group(
    frames: int = 1,
    trigger: str = "Immediate",
    wait_time: int = 1,
    wait_units: str = "S",
    run_time: int = 1,
    run_units: str = "S",
    wait_pulses: list[int] = [0, 0, 0, 0],  # noqa
    run_pulses: list[int] = [1, 1, 1, 1],  # noqa
) -> MsgGenerator:
    STORED_PROFILE = get_profile()

    if STORED_PROFILE is None:
        LOGGER.info("No profile has been set, a blank profiles has been created")
        STORED_PROFILE = Profile()

    STORED_PROFILE.append_group(
        Group(
            frames=frames,
            trigger=trigger,
            wait_time=wait_time,
            wait_units=wait_units,
            run_time=run_time,
            run_units=run_units,
            wait_pulses=wait_pulses,
            run_pulses=run_pulses,
        )
    )

    yield from bps.null()


def delete_group(n: int = 1) -> MsgGenerator:
    STORED_PROFILE = get_profile()

    if STORED_PROFILE is None:
        raise ValueError("No profile has been set, use set_profile")

    STORED_PROFILE.delete_group(n)

    yield from bps.null()


def create_steps(start: float, stop: float | None, step: float | None):
    if (step is not None) and (stop < start) and (step > 0):  # type: ignore
        step = -step

    if (stop is None) and (step is not None):
        raise ValueError("If step is provided, stop must also be provided")
    elif (step is None) and (stop is not None):
        step = stop - start

    if (step is None) and (stop is None):
        step_list = [start]
    else:
        step_list = list(np.arange(start, stop, step))
        step_list = [i.item() for i in step_list]

    # LOGGER.info(f"Steps: {step_list}")

    return step_list


@attach_data_session_metadata_decorator()
@bpp.baseline_decorator(DEFAULT_BASELINE)
@validate_call(config={"arbitrary_types_allowed": True})
def step_scan(
    start: float,
    stop: float,
    num: int,
    axis: Motor,
    detectors: list[StandardReadable],
) -> MsgGenerator:
    LOGGER.info(f"Running gda style step scan with detectors: {detectors}")

    # step_list = create_steps(start, stop, step)
    yield from bsp.scan(detectors, axis, start, stop, num)


@attach_data_session_metadata_decorator()
@bpp.baseline_decorator(DEFAULT_BASELINE)
@validate_call(config={"arbitrary_types_allowed": True})
def step_rscan(
    start: float,
    stop: float,
    num: int,
    axis: Motor,
    detectors: list[StandardReadable],
) -> MsgGenerator:
    LOGGER.info(f"Running gda style rstep scan with detectors: {detectors}")

    # step_list = create_steps(start, stop, step)
    yield from bsp.rel_scan(detectors, axis, start, stop, num)


@attach_data_session_metadata_decorator()
@bpp.baseline_decorator(DEFAULT_BASELINE)
@validate_call(config={"arbitrary_types_allowed": True})
def centre_sample(
    start: float,
    stop: float,
    step: float,
    axis: Motor,
    detectors: list[StandardReadable] = FAST_DETECTORS,
) -> MsgGenerator:
    step_list = create_steps(start, stop, step)

    summed_values = []

    for step in step_list:
        yield from bps.mv(axis, step)
        value = yield from bps.rd(*detectors)
        summed_values.append(np.sum(value))

    max_index = np.argmax(summed_values)
    centre_point = summed_values[max_index]

    yield from bps.mv(axis, centre_point)
