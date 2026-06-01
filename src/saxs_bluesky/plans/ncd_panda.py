import copy
from functools import partial
from typing import Annotated, Any

import bluesky.plan_stubs as bps
import bluesky.plans as bsp
import bluesky.preprocessors as bpp
import numpy as np
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.devices.hutch_shutter import HutchShutter, ShutterDemand
from dodal.devices.motors import Motor
from dodal.devices.tetramm import TetrammDetector, TetrammTrigger
from dodal.log import LOGGER
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    StandardReadable,
    TriggerInfo,
)
from ophyd_async.epics.adpilatus import PilatusDetector
from ophyd_async.fastcs.panda import (
    HDFPanda,
    PandaBitMux,
    SeqTableInfo,
    StaticSeqTableTriggerLogic,
)
from ophyd_async.plan_stubs import (
    ensure_connected,
)
from ophyd_async.plan_stubs._wait_for_awaitable import wait_for_awaitable
from pydantic import validate_call

from saxs_bluesky.stubs.panda_stubs import (
    check_and_apply_panda_settings,
    fly_and_collect_with_wait,
    wait_until_complete,
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


# def stage_and_prepare_detectors(
#     detectors: list[StandardDetector],
#     flyer: StandardFlyer,
#     trigger_info: TriggerInfo,
#     group="det_atm",
# ):
#     """

#     Iterates through all of the detectors specified and prepares them.

#     """

#     yield from bps.stage_all(*detectors, flyer, group=group)

#     for det in detectors:
#         ###this tells the detector how may triggers to expect and sets the CAN aquire
#         yield from bps.prepare(det, trigger_info, wait=False, group=group)

#     yield from bps.wait(group=group, timeout=DEFAULT_TIMEOUT)

import asyncio
import threading
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from functools import partial

from bluesky.run_engine import RunEngine
from ophyd_async.core import SignalR


class MySuspenderBase(metaclass=ABCMeta):
    """An ABC to manage the callbacks between asyincio and pyepics.


    Parameters
    ----------
    signal : `ophyd.Signal`
        The signal to watch for changes to determine if the
        scan should be suspended

    sleep : float, optional
        How long to wait in seconds after the resume condition is met
        before marking the event as done.  Defaults to 0

    pre_plan : iterable or iterator or generator function, optional
            a generator, list, or similar containing `Msg` objects

    post_plan : iterable or iterator or generator function, optional
            a generator, list, or similar containing `Msg` objects

    tripped_message : str, optional
        Message to include in the trip notification
    """

    def __init__(
        self,
        signal: SignalR,
        *,
        sleep=0,
        pre_plan=None,
        post_plan=None,
        tripped_message="",
    ):
        """ """
        self.RE = None
        self._ev = None
        self._tripped = False
        self._tripped_message = tripped_message
        self._sleep = sleep
        self._lock = threading.Lock()
        self._sig = signal
        self._pre_plan = pre_plan
        self._post_plan = post_plan

    def __repr__(self):
        return (
            "{}({!r}, sleep={}, pre_plan={}, post_plan={}, tripped_message={})".format(  # noqa: UP032
                type(self).__name__,
                self._sig,
                self._sleep,
                self._pre_plan,
                self._post_plan,
                self._tripped_message,
            )
        )

    def install(self, RE: RunEngine, *, event_type=None):
        """Install callback on signal

        This (re)installs the required callbacks at the pyepics level

        Parameters
        ----------

        RE : RunEngine
            The run engine instance this should work on

        event_type : str, optional
            The event type (subscription type) to watch
        """
        with self._lock:
            self.RE = RE
        self._sig.subscribe(self)  # , event_type=event_type, run=True)

    def remove(self):
        """Disable the suspender

        Removes the callback at the pyepics level
        """
        self._sig.clear_sub(self)
        with self._lock:
            if self.RE is not None:
                self.__set_event(self.RE._loop)
            self.RE = None
            self._tripped = False

    @abstractmethod
    def _should_suspend(self, value):
        """
        Determine if the current value of the signal is such
        that we need to tell the scan to suspend

        Parameters
        ----------
        value : object
            The value to evaluate to determine if we should
            suspend

        Returns
        -------
        suspend : bool
            True means suspend
        """
        raise NotImplementedError()

    @abstractmethod
    def _should_resume(self, value):
        """
        Determine if the scan is ready to automatically
        restart.

        Parameters
        ----------
        value : object
            The value to evaluate to determine if we should
            resume

        Returns
        -------
        suspend : bool
            True means resume
        """
        raise NotImplementedError()

    def __call__(self, value, **kwargs):
        """Make the class callable so that we can
        pass it off to the ophyd callback stack.

        This expects the massive blob that comes from ophyd
        """
        with self._lock:
            if self.RE is None:
                return
            loop = self.RE._loop

            if self._should_suspend(value):
                self._tripped = True
                # this does dirty things with internal state
                if self._ev is None and self.RE is not None:
                    self.__make_event()
                    if self._ev is None:
                        raise RuntimeError("Could not create the suspender event")
                    cb = partial(
                        self.RE.request_suspend,
                        self._ev.wait,
                        pre_plan=self._pre_plan,
                        post_plan=self._post_plan,
                        justification=self._get_justification(),
                    )
                    if self.RE.state.is_running:
                        loop.call_soon_threadsafe(cb)
            elif self._should_resume(value):
                self.__set_event(loop)
                self._tripped = False

    def __make_event(self):
        """Make or return the asyncio.Event to use as a bridge."""
        assert self._lock.locked()
        if self._ev is None and self.RE is not None:
            if threading.get_ident() == getattr(self.RE._loop, "_thread_id", "unknown"):
                self._ev = asyncio.Event()
                return self._ev
            else:
                th_ev = threading.Event()

                def really_make_the_event():
                    self._ev = asyncio.Event()
                    th_ev.set()

                h = self.RE._loop.call_soon_threadsafe(really_make_the_event)
                if not th_ev.wait(0.1):
                    h.cancel()
        return self._ev

    def __set_event(self, loop):
        """Notify the event that it can resume"""
        assert self._lock.locked()
        if self._ev:
            ev = self._ev
            sleep = self._sleep

            def local():
                ts = (datetime.now() + timedelta(seconds=sleep)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(
                    f"Suspender {self!r} reports a return to nominal "
                    f"conditions. Will sleep for {sleep} seconds and then "
                    f"release suspension at {ts}."
                )
                # we can use call_later here because this function
                # is scheduled to be run in the event loop thread
                # by the `call_soon_threadsafe` call just below.
                loop.call_later(sleep, ev.set)

            loop.call_soon_threadsafe(local)
        # clear that we have an event
        self._ev = None

    def get_futures(self):
        """Return a list of futures to wait on.

        This will only work correctly if this suspender is 'installed'
        and watching a signal

        Returns
        -------
        futs : list
            List of futures to wait on

        justification : str
            String explaining why the suspender is tripped
        """
        if not self.tripped:
            return [], ""
        with self._lock:
            return [self.__make_event().wait], self._get_justification()

    @property
    def tripped(self):
        return self._tripped

    def _get_justification(self):
        if not self.tripped:
            return ""

        template = "Suspender of type {} stopped by signal {!r}"
        just = template.format(self.__class__.__name__, self._sig)
        return ": ".join(s for s in (just, self._tripped_message) if s)


class CountRateProtectionSuspender(MySuspenderBase):
    def __init__(
        self,
        max_signal,
        min_exposure_time_seconds: float,
        close_shutters_plan,
    ):
        self.min_exposure_time_seconds = min_exposure_time_seconds
        self.close_shutters_plan = close_shutters_plan

        super().__init__(
            max_signal,
            sleep=0,
            pre_plan=self.abort,
            post_plan=None,
        )

    def abort(self):
        yield from self.close_shutters_plan()
        if self.last_value > 1e6:
            raise Exception(
                f"Detector saturated with {self.last_value} counts, assuming countrate exceeded and closing shutters"
            )
        else:
            raise Exception(
                f"Countrate likely exceeded. {self.last_value} counts seen and minimum collection time is {self.min_exposure_time_seconds}s"
            )

    def _should_suspend(self, value):
        self.last_value = value[self._sig.name]["value"]
        return (
            self.last_value > 1e6
            or self.last_value / self.min_exposure_time_seconds > 4e6
        )

    def _should_resume(self, value):
        return False

    def _get_justification(self):
        return ""


def return_deadtime(
    detectors: list[StandardDetector], exposure: float = 1.0
) -> MsgGenerator[np.ndarray]:
    """
    Given a list of connected detector devices, and an exposure time,
    it returns an array of the deadtime for each detector
    """

    deadtimes = []
    for det in detectors:
        (det_deadtime,) = yield from bps.wait_for([det.get_trigger_deadtime])
        deadtimes.append(det_deadtime.result()[1])

    deadtime = (
        np.array(deadtimes)  # noqa: SLF001
        + 20e-6  # Buffer added to deadtime to handle minor discrepencies between det
        # and panda clocks
    )
    return deadtime


def generate_repeated_trigger_info(
    profile: Profile,
    max_deadtime: float,
    livetime: float,
    trigger=DetectorTrigger.EXTERNAL_LEVEL,
) -> list[TriggerInfo]:
    repeated_trigger_info = []

    # [3, 1, 1, 1, 1] or something
    n_triggers = sum([group.frames for group in profile.groups if group.run_pulses[2]])
    repeats = profile.repeats

    LOGGER.info(f"Setting up with {profile}")

    if profile.multiplier is not None:
        for multiplier in profile.multiplier:
            trigger_info = TriggerInfo(
                number_of_events=n_triggers * repeats,
                trigger=trigger,
                deadtime=max_deadtime,
                livetime=profile.duration,
                collections_per_event=multiplier,
                exposure_timeout=100000,  # Needs a fix
            )

            repeated_trigger_info.append(trigger_info)

    return repeated_trigger_info


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

    for out in CONFIG.LVDSOUT.keys():
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
    ensure_panda_connected: bool = True,
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
    if ensure_panda_connected:
        yield from ensure_connected(panda)  # ensure the panda is connected

    LOGGER.info("Using the following detectors:")
    LOGGER.info("")
    for det in detectors:
        LOGGER.info(str(det))

    detector_deadtime = yield from return_deadtime(
        detectors=list(detectors), exposure=profile.duration
    )

    max_deadtime = max(detector_deadtime)

    # load Panda setting to panda
    if force_load:
        yield from check_and_apply_panda_settings(
            panda, BL, CONFIG.SETTINGS_NAME, panda.name
        )

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


def cleanup_tetramms(tetramms: list[TetrammDetector]):
    """In general we want to leave the tetramms free running so that we can monitor them
    in e.g. GDA"""
    for tetramm in tetramms:
        yield from bps.mv(tetramm.driver.trigger_mode, TetrammTrigger.FREE_RUN)
        yield from bps.abs_set(tetramm.driver.acquire, True)


@validate_call(config={"arbitrary_types_allowed": True})
def run_panda_triggering(
    panda: HDFPanda = DEFAULT_PANDA,
    baseline: list[StandardReadable] = DEFAULT_BASELINE,
    metadata: dict[str, Any] | None = None,
    shutters: list[HutchShutter] = [inject("saxs_shutter"), inject("eh_shutter")],
) -> MsgGenerator:
    """

    This will run whatever flyscanning settings
    are currently loaded on the PandA and start it triggering

    """

    if STORED_TRIGGER_INFO is None:
        raise ValueError("No trigger info has been set, use set_trigger_info")
    else:
        trigger_info: TriggerInfo = STORED_TRIGGER_INFO  # type: ignore

    if STORED_DETECTORS is None:
        raise ValueError("No detectors have been set, use set_detectors")
    else:
        detectors: list[StandardDetector] = STORED_DETECTORS  # type: ignore

    if STORED_PROFILE is None:
        raise ValueError("No profile has been set, use configure_panda_triggering")
    else:
        profile: Profile = STORED_PROFILE  # type: ignore

    count_times = []
    for group in profile.groups:
        # Assumes det only triggered on run
        if group.run_pulses[2]:  # Pull into det const
            count_times.extend([group.run_time_s] * group.frames)

    tetramms = [obj for obj in detectors if isinstance(obj, TetrammDetector)]
    pilatus_detectors = [obj for obj in detectors if isinstance(obj, PilatusDetector)]

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
        "count_time": count_times,
        "hints": {},
    }
    _md.update(metadata or {})

    def close_shutters(shutters):
        for shutter in shutters:
            yield from bps.abs_set(shutter, ShutterDemand.CLOSE, group="shutter_close")
        yield from bps.wait("shutter_close")

    suspenders = [
        CountRateProtectionSuspender(
            detector.get_plugin("stats").cursor_x,
            profile.min_livetime,
            partial(close_shutters, shutters),
        )
        for detector in pilatus_detectors
    ]

    ##################

    @bpp.baseline_decorator(baseline)
    @bpp.run_decorator(md=_md)
    @bpp.finalize_decorator(partial(cleanup_tetramms, tetramms))
    @bpp.suspend_decorator(suspenders)
    def inner_run():
        # get the loaded seq table
        panda_seq_table = panda.seq[CONFIG.DEFAULT_SEQ]
        # flyer and prepare fly, sets the sequencers table
        trigger_logic = StaticSeqTableTriggerLogic(panda_seq_table)
        flyer = StandardFlyer(trigger_logic)

        nonlocal detectors

        # detectors = detectors + [panda]  # panda must be added so we can get HDF
        all_devices = detectors + DEFAULT_BASELINE

        # STAGE SETS HDF WRITER TO ON
        yield from bps.stage_all(*all_devices, flyer, group="setup")

        LOGGER.info("Done stage")

        for det in tetramms:
            ###this tells the detector how may triggers to expect and sets the CAN aquir
            yield from bps.abs_set(det.driver.values_per_reading, 10)
            tetramm_trigger = copy.deepcopy(trigger_info)
            tetramm_trigger.trigger = DetectorTrigger.EXTERNAL_EDGE
            tetramm_trigger.livetime = profile.min_livetime
            yield from bps.prepare(det, tetramm_trigger, group="setup")

        for det in [obj for obj in detectors if not isinstance(obj, TetrammDetector)]:
            ###this tells the detector how may triggers to expect and sets the CAN aquir
            yield from bps.prepare(det, trigger_info, group="setup")

        yield from bps.wait(group="setup", timeout=DEFAULT_TIMEOUT * len(detectors))

        LOGGER.info("Done prepare")

        yield from fly_and_collect_with_wait(
            stream_name="primary",
            detectors=list(detectors),
            flyer=flyer,
        )

        LOGGER.info("Done flying")

        yield from wait_until_complete(panda_seq_table.active, False)

        # turn off all pulses whether or not using
        yield from set_panda_pulses(
            panda=panda, pulses=list(np.array(range(4)) + 1), setting="disarm"
        )

        # start diabling and unstaging everything
        yield from bps.unstage_all(*all_devices, flyer)  # stops the hdf capture mode

    ########## The main part
    yield from inner_run()
    ##########


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
    ensure_panda_connected: bool = True,
    force_load: bool = False,
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
        ensure_panda_connected=ensure_panda_connected,
        force_load=force_load,
    )

    yield from run_panda_triggering()


@validate_call(config={"arbitrary_types_allowed": True})
def set_detectors(
    detectors: list[StandardDetector],
) -> MsgGenerator:
    global STORED_DETECTORS
    STORED_DETECTORS = detectors

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

    STORED_PROFILE = Profile(repeats=repeats, multiplier=multiplier)

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
    stored_profile = get_profile()

    if stored_profile is None:
        LOGGER.info("No profile has been set, a blank profiles has been created")
        stored_profile = Profile()

    stored_profile.append_group(
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
    stored_profile = get_profile()

    if stored_profile is None:
        raise ValueError("No profile has been set, use set_profile")

    stored_profile.delete_group(n)

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

    for n, step in enumerate(step_list):
        LOGGER.info(f"Step {n}: {step}")

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
