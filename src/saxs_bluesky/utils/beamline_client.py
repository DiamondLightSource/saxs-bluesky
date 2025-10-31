from collections.abc import Callable
from pathlib import Path

from blueapi._version import __version__
from blueapi.cli.updates import CliEventRenderer
from blueapi.client.client import BlueapiClient
from blueapi.client.event_bus import AnyEvent, BlueskyStreamingError
from blueapi.client.rest import BlueskyRemoteControlError
from packaging.version import Version

if Version(__version__) > Version("1.6.1"):
    from blueapi.client.rest import (
        InvalidParametersError,
        UnauthorisedAccessError,
        UnknownPlanError,
    )
else:
    from blueapi.client.rest import InvalidParameters as InvalidParametersError
    from blueapi.client.rest import UnauthorisedAccess as UnauthorisedAccessError
    from blueapi.client.rest import UnknownPlan as UnknownPlanError

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


class BlueAPIPythonClient(BlueapiClient):
    """A simple BlueAPI client for running bluesky plans."""

    def __init__(
        self,
        beamline: str,
        blueapi_config_path: str | Path,
        instrument_session: str,
        callback: bool = False,
    ):
        self.beamline = beamline
        self.instrument_session = instrument_session
        self.callback = callback

        blueapi_config_path = Path(blueapi_config_path)

        config_loader = ConfigLoader(ApplicationConfig)
        config_loader.use_values_from_yaml(blueapi_config_path)
        loaded_config = config_loader.load()
        blueapi_class = BlueapiClient.from_config(loaded_config)
        super().__init__(blueapi_class._rest, blueapi_class._events)  # noqa

    def run(
        self,
        plan: str | Callable,
        timeout: float | None = None,
        **kwargs,
    ):
        """Run a bluesky plan via BlueAPI."""
        if isinstance(plan, str):
            plan_name = plan
        elif hasattr(plan, "__name__"):
            plan_name = plan.__name__
        else:
            raise ValueError("Must be a str or a bluesky plan")

        task = TaskRequest(
            name=plan_name,
            params=kwargs,
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

                resp = self.run_task(task, on_event=on_event, timeout=timeout)

                if (
                    (resp.task_status is not None)
                    and (resp.task_status.task_complete)
                    and (not resp.task_status.task_failed)
                ):
                    print(f"{plan_name} succeeded")

                return

            except UnknownPlanError as up:
                raise Exception(f"Plan '{plan_name}' was not recognised: {up}") from up
            except UnauthorisedAccessError as ua:
                raise Exception(f"Unauthorised request {ua}") from ua
            except InvalidParametersError as ip:
                raise Exception(f"{ip.message()}: {ip}") from ip
            except (BlueskyRemoteControlError, BlueskyStreamingError) as e:
                raise Exception(f"server error with this message: {e}") from e
            except ValueError as ve:
                raise Exception(f"task could not run: {ve}") from ve

        else:
            server_task = self.create_and_start_task(task)
            print(f"{plan_name} task sent as {server_task.task_id}")

    def return_detectors(self) -> list[StandardReadable]:
        """Return a list of StandardReadable for the current beamline."""
        devices = self.get_devices().devices
        return [inject(d.name) for d in devices]

    def change_session(self, new_session: str) -> None:
        """Change the instrument session for the client."""
        print(f"New instrument session: {new_session}")
        self.instrument_session = new_session
