import time
import warnings
from collections.abc import Callable
from pathlib import Path

from blueapi.cli.updates import CliEventRenderer
from blueapi.client.client import BlueapiClient
from blueapi.client.event_bus import AnyEvent
from blueapi.client.rest import BlueskyRemoteControlError
from blueapi.config import (
    ApplicationConfig,
    ConfigLoader,
)
from blueapi.core import DataEvent
from blueapi.service.model import TaskRequest
from blueapi.worker import ProgressEvent
from bluesky.callbacks.best_effort import BestEffortCallback
from dodal.common import inject
from ophyd_async.core import StandardReadable

warnings.filterwarnings("ignore")


class BlueAPIPythonClient(BlueapiClient):
    """A simple BlueAPI client for running bluesky plans."""

    def __init__(
        self,
        beamline: str,
        blueapi_config_path: str | Path,
        instrument_session: str,
        callback: bool = True,
        timeout: int | float | None = None,
    ):
        self.beamline = beamline
        self.instrument_session = instrument_session
        self.callback = callback
        self.retries = 5
        self.timeout = timeout

        blueapi_config_path = Path(blueapi_config_path)

        config_loader = ConfigLoader(ApplicationConfig)
        config_loader.use_values_from_yaml(blueapi_config_path)
        loaded_config = config_loader.load()
        blueapi_class = BlueapiClient.from_config(loaded_config)
        super().__init__(blueapi_class._rest, blueapi_class._events)  # noqa

    def _convert_args_to_kwargs(self, plan: Callable, args: tuple) -> dict:
        arg_names = plan.__code__.co_varnames

        inferred_kwargs = {}

        for key, val in zip(arg_names, args):  # noqa intentionally not strict
            inferred_kwargs[key] = val
        params = inferred_kwargs
        return params

    def _args_and_kwargs_to_params(
        self, plan: Callable | str, args: tuple, kwargs: dict
    ) -> dict:
        if not args and not kwargs:
            params = {}
            return params
        elif (
            args
            and (not kwargs)
            and hasattr(plan, "__code__")
            and not isinstance(plan, str)
        ):
            params = self._convert_args_to_kwargs(plan, args)
            return params

        elif (
            args and kwargs and hasattr(plan, "__code__") and not isinstance(plan, str)
        ):
            params = self._convert_args_to_kwargs(plan, args)
            params.update(kwargs)
            return params
        elif isinstance(plan, str) and not kwargs:
            raise ValueError("If you pass the bluesky plan str, you must give kwargs")
        elif isinstance(plan, str) and args and (not kwargs):
            raise ValueError(
                "If you pass the bluesky plan str, you must give kwargs only"
            )
        else:
            raise ValueError("Could not infer parameters from args and kwargs")

    def run(self, plan: str | Callable, *args, **kwargs):
        """Run a bluesky plan via BlueAPI."""

        if isinstance(plan, str):
            plan_name = plan
        elif hasattr(plan, "__name__"):
            plan_name = plan.__name__
        else:
            raise ValueError("Must be a str or a bluesky plan funtcion")

        params = self._args_and_kwargs_to_params(plan, args=args, kwargs=kwargs)

        task = TaskRequest(
            name=plan_name,
            params=params,
            instrument_session=self.instrument_session,
        )
        if self.callback:
            try:
                progress_bar = CliEventRenderer()
                callback = BestEffortCallback()

                def on_event(event: AnyEvent) -> None:
                    if isinstance(event, ProgressEvent):
                        progress_bar.on_progress_event(event)
                    elif isinstance(event, DataEvent):
                        callback(event.name, event.doc)

                resp = self.run_task(task, on_event=on_event, timeout=self.timeout)

                if (
                    (resp.task_status is not None)
                    and (resp.task_status.task_complete)
                    and (not resp.task_status.task_failed)
                ):
                    print(f"{plan_name} succeeded")

                return

            except Exception as e:
                raise Exception(f"Task could not run: {e}") from e

        else:
            for _ in range(self.retries):
                try:
                    server_task = self.create_and_start_task(task)
                    print(f"{plan_name} task sent as {server_task.task_id}")
                    break
                except BlueskyRemoteControlError:
                    time.sleep(1)
            return

    def return_detectors(self) -> list[StandardReadable]:
        """Return a list of StandardReadable for the current beamline."""
        devices = self.get_devices().devices
        return [inject(d.name) for d in devices]

    def change_session(self, new_session: str) -> None:
        """Change the instrument session for the client."""
        print(f"New instrument session: {new_session}")
        self.instrument_session = new_session

    def show_plans(self):
        plans = self.get_plans().plans
        for plan in plans:
            print(plan.name)
        print(f"Total plans: {len(plans)} \n")

    def show_devices(self):
        devices = self.get_devices().devices
        for dev in devices:
            print(dev.name)
        print(f"Total devices: {len(devices)} \n")
