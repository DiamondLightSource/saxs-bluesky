import json
import logging
import time
from collections import deque

import stomp

logger = logging.getLogger(__name__)


class DaqScanListener(stomp.ConnectionListener):
    def __init__(self):
        self.queue = deque()

    def on_error(self, frame):
        print(f"received an error {frame.body}")

    def on_message(self, frame):
        m = json.loads(frame.body)
        self.queue.append(m)


class DaqMessenger:
    def __init__(self, beamline):
        self.beamline = beamline

    def connect(self):
        self.conn = stomp.Connection(
            [(self.beamline, 61613)], auto_content_length=False
        )
        self.conn.connect()

    def disconnect(self):
        self.conn.disconnect()

    def on_scan(self, message_function, sleep=1):
        dsl = DaqScanListener()
        self.conn.set_listener("scan", dsl)
        self.conn.subscribe(destination="/topic/gda.messages.scan", id=1, ack="auto")

        while 1:
            while dsl.queue:
                m = dsl.queue.popleft()
                message_function(m)
            time.sleep(sleep)

    def send_file(self, path):
        message = json.dumps({"filePath": path})
        destination = "/topic/org.dawnsci.file.topic"
        self._send_message(destination, message)

    def send_start(self, path):
        message = json.dumps(
            {"filePath": path, "status": "STARTED", "swmrStatus": "ENABLED"}
        )
        destination = "/topic/gda.messages.processing"
        self._send_message(destination, message)

    def send_update(self, path):
        message = json.dumps(
            {"filePath": path, "status": "UPDATED", "swmrStatus": "ACTIVE"}
        )
        destination = "/topic/gda.messages.processing"
        self._send_message(destination, message)

    def send_finished(self, path):
        message = json.dumps(
            {"filePath": path, "status": "FINISHED", "swmrStatus": "ACTIVE"}
        )
        destination = "/topic/gda.messages.processing"
        self._send_message(destination, message)

    def send_poni(self, path, status, message):
        """
        styatus is ERROR WARN OK
        """
        message = json.dumps(
            {"calibration_filepath": path, "status": status, "message": message}
        )
        destination = "/topic/gda.messages.calibration.xrd2"
        self._send_message(destination, message)

    def _send_message(self, destination, message):
        self.conn.send(destination=destination, body=message, ack="auto")


if __name__ == "__main__":
    bl = "i22"
    bl_control_machine = bl + "-control"

    filepath_out = "/dls/i22/data/2024/cm56789-1/mythen_nx/test/data.dat"

    try:
        daq = DaqMessenger(bl_control_machine)
        daq.connect()
        daq.send_file(str(filepath_out))  # sends message to GDA to plot

    except Exception as e:
        print(f"{e}: No messenger")
