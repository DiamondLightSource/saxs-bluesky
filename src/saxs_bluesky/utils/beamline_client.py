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

    def run(self, plan_name: str, params: dict):
        task = TaskRequest(
            name=plan_name,
            params=params,
            instrument_session=self.instrument_session,
        )

        progress_bar = CliEventRenderer()
        callback = BestEffortCallback()

        def on_event(event: AnyEvent) -> None:
            if isinstance(event, ProgressEvent):
                progress_bar.on_progress_event(event)
            elif isinstance(event, DataEvent):
                callback(event.name, event.doc)

        # response = self.create_and_start_task(task)
        response = self.run_task(task, on_event=on_event, timeout=10)
        print(response)
        if response.task_status is not None and not response.task_status.task_failed:
            print("Plan Succeeded")
