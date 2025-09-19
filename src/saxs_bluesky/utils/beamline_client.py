from collections.abc import Callable
from pathlib import Path

from blueapi.cli.updates import CliEventRenderer
from blueapi.client.client import BlueapiClient
from blueapi.client.event_bus import AnyEvent
from blueapi.config import (
    ApplicationConfig,
    ConfigLoader,
)
from blueapi.core import DataEvent
from blueapi.service.model import TaskRequest
from blueapi.worker import ProgressEvent
from bluesky.callbacks.best_effort import BestEffortCallback
from dodal.common import inject


class BlueAPIPythonClient(BlueapiClient):
    def __init__(
        self, BL: str, blueapi_config_path: str | Path, instrument_session: str
    ):
        self.BL = BL
        self.instrument_session = instrument_session

        blueapi_config_path = Path(blueapi_config_path)

        config_loader = ConfigLoader(ApplicationConfig)
        config_loader.use_values_from_yaml(blueapi_config_path)
        loaded_config = config_loader.load()
        blueapi_class = BlueapiClient.from_config(loaded_config)
        super().__init__(blueapi_class._rest, blueapi_class._events)  # noqa

    def run(self, plan: str | Callable, **kwargs):
        if isinstance(plan, str):
            plan_name = plan
        else:
            plan_name = plan.__name__

        task = TaskRequest(
            name=plan_name,
            params=kwargs,
            instrument_session=self.instrument_session,
        )

        progress_bar = CliEventRenderer()
        callback = BestEffortCallback()

        def on_event(event: AnyEvent) -> None:
            if isinstance(event, ProgressEvent):
                progress_bar.on_progress_event(event)
            elif isinstance(event, DataEvent):
                callback(event.name, event.doc)

        response = self.run_task(task, on_event=on_event, timeout=None)
        print(response)
        if response.task_status is not None and not response.task_status.task_failed:
            print("Plan Succeeded")

    def return_detectors(self):
        devices = self.get_devices().devices
        return [inject(d.name) for d in devices]


if __name__ == "__main__":
    BL = "i22"
    blueapi_config_path = f"./src/saxs_bluesky/blueapi_configs/{BL}_blueapi_config.yaml"
    client = BlueAPIPythonClient(BL, blueapi_config_path, "None")

    print(client.return_detectors())
