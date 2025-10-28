import json
import time
from collections import deque

from saxs_bluesky.logging.bluesky_messenger import MessageUnpacker, ScanListener


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


def test_scan_messenger():
    listener = ScanListener(maxlen=10)

    class MockMessage:
        def __init__(self, body):
            self.body = json.dumps({"body": body})

    listener.on_message(MockMessage("test message 1"))
    listener.on_error(MockMessage("error message 1"))

    assert len(listener.messages) == 1
