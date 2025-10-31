import json
import time
from collections import deque
from unittest.mock import Mock

import pytest
from stomp.connect import StompConnection11 as Connection  # type: ignore

from saxs_bluesky.logging.bluesky_messenger import (
    MessageUnpacker,
    ScanListener,
    StompMessenger,
)


@pytest.fixture
def mock_connection() -> Mock:
    return Mock(spec=Connection)


@pytest.fixture
def connected_messenger(mock_connection: Mock) -> StompMessenger:
    connected_messenger = StompMessenger(
        host="http://localhost",
        beamline="ixx",
        port=8080,
        auto_connect=False,
    )
    connected_messenger.conn = mock_connection
    connected_messenger.connect()
    connected_messenger.subscribe()

    return connected_messenger


def test_message_unpacker():
    sample_message = {
        "header": {
            "uid": "12345",
            "time": time.time(),
            "msg_type": "start",
        },
        "data": {
            "key1": "value1",
            "key2": 42,
        },
    }

    unpacked_message = MessageUnpacker.unpack_dict(sample_message)

    assert isinstance(unpacked_message, deque)
    assert "time: " in unpacked_message[1]


def test_scan_messenger():
    listener = ScanListener(maxlen=10)

    class MockMessage:
        def __init__(self, body):
            self.body = json.dumps({"body": body})

    listener.on_message(MockMessage("test message 1"))
    listener.on_error(MockMessage("error message 1"))

    assert len(listener.messages) == 1


def test_messenger_creation():
    messenger = StompMessenger(
        host="localhost",
        beamline="test_beamline",
        port=11111,
        username="user",
        password="pass",
        destination="/queue/test",
        auto_connect=False,
    )

    assert messenger.host == "localhost"
    assert messenger.port == 11111
    assert messenger.beamline == "test_beamline"


def test_messenger_no_port_default():
    messenger = StompMessenger(
        host="localhost",
        beamline="ixx",
        destination="/queue/test",
        auto_connect=False,
        port=None,
    )
    assert messenger.port == 61613


def test_messenger_destination_default():
    messenger = StompMessenger(
        host="localhost",
        beamline="ixx",
        auto_connect=False,
    )
    assert messenger.destination == [
        "/topic/public.worker.event",
        "/topic/gda.messages.scan",
    ]


def test_messenger_host_default():
    messenger = StompMessenger(
        beamline="ixx",
        auto_connect=False,
    )
    assert messenger.host == "ixx-rabbitmq-daq.diamond.ac.uk"


def test_messenger_stops():
    messenger = StompMessenger(
        auto_connect=False,
        host="localhost",
    )
    assert messenger.run
    messenger.stop()
    assert not messenger.run


def test_messenger_fails_without_host_or_beamline():
    with pytest.raises(ValueError):
        StompMessenger(
            auto_connect=False,
        )


def test_messenger_listener():
    messenger = StompMessenger(
        beamline="ixx",
        auto_connect=False,
    )

    messenger.scan_listener.messages.append({"body": "test message"})
    messenger.listen(max_iter=5, interval=0.01)


def test_messenger_send(connected_messenger: StompMessenger):
    connected_messenger.listen(max_iter=5, interval=0.01)
    connected_messenger.send_start("/path/to/file")
    connected_messenger.send_update("/path/to/file")
    connected_messenger.send_finished("/path/to/file")
    connected_messenger.send_file("/path/to/file")


def test_messenger_disconnect(connected_messenger: StompMessenger):
    connected_messenger.listen(max_iter=5, interval=0.01)
    connected_messenger.disconnect()
