import os
from unittest.mock import Mock, patch

import pytest
from blueapi.client.client import BlueapiClient
from blueapi.client.event_bus import EventBusClient
from blueapi.client.rest import BlueapiRestClient

import saxs_bluesky.blueapi_configs
from saxs_bluesky.plans.ncd_panda import configure_panda_triggering
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient


@pytest.fixture(autouse=True)
def client():
    beamline = "i22"
    blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{beamline}_blueapi_config.yaml"  # noqa
    client = BlueAPIPythonClient(
        beamline, blueapi_config_path, "cm12345-1", callback=True
    )

    client._rest = Mock(BlueapiRestClient)
    client._events = Mock(EventBusClient)

    client._events.__enter__ = Mock(return_value=client._events)
    client._events.__exit__ = Mock(return_value=None)

    return client


@pytest.fixture(autouse=True)
def client_without_callback():
    beamline = "i22"
    blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{beamline}_blueapi_config.yaml"  # noqa
    client_without_callback = BlueAPIPythonClient(
        beamline, blueapi_config_path, "cm12345-1", callback=False
    )

    return client_without_callback


def test_blueapi_python_client(client: BlueAPIPythonClient):
    assert isinstance(client, BlueapiClient)
    assert isinstance(client, BlueAPIPythonClient)


def test_blueapi_python_client_change_session(client: BlueAPIPythonClient):
    assert client.beamline == "i22"
    client.change_session("9999")
    assert client.instrument_session == "9999"


def test_blueapi_python_client_run(client: BlueAPIPythonClient):
    # Patch instance methods so run executes but no re calls happen.
    with (
        patch.object(client, "run_task", return_value=Mock()),
        patch.object(
            client, "create_and_start_task", return_value=Mock(task_id="t-fake")
        ),
        patch.object(client, "create_task", return_value=Mock(task_id="t-fake")),
        patch.object(client, "start_task", return_value=Mock(task_id="t-fake")),
    ):
        assert client._events is not None
        # Ensure the mocked event client can be used as a context manager if run uses it
        client._events.__enter__ = Mock(return_value=client._events)
        client._events.__exit__ = Mock(return_value=None)

        # Call run while the instance methods are patched
        client.run(configure_panda_triggering)


def test_blueapi_python_client_without_callback_run(
    client_without_callback: BlueAPIPythonClient,
):
    # Patch instance methods so run executes but no calls happen
    with (
        patch.object(client_without_callback, "run_task", return_value=Mock()),
        patch.object(
            client_without_callback,
            "create_and_start_task",
            return_value=Mock(task_id="t-fake"),
        ),
        patch.object(
            client_without_callback, "create_task", return_value=Mock(task_id="t-fake")
        ),
        patch.object(
            client_without_callback, "start_task", return_value=Mock(task_id="t-fake")
        ),
    ):
        # Ensure the mocked event client can be used as a context manager if run uses it
        client_without_callback._events = Mock(EventBusClient)
        client_without_callback._events.__enter__ = Mock(
            return_value=client_without_callback._events
        )
        client_without_callback._events.__exit__ = Mock(return_value=None)

        client_without_callback.run(configure_panda_triggering)
