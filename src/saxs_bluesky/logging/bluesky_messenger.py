import json
from collections import deque
from pathlib import Path
from time import sleep

import stomp


class MessageUnpacker:
    messages = deque()

    @staticmethod
    def unpack_dict(unpacked: dict):
        for key, value in unpacked.items():
            if isinstance(value, dict):
                MessageUnpacker.unpack_dict(value)
            else:
                MessageUnpacker.messages.append(f"{key}: {value}")

        return MessageUnpacker.messages


class ScanListener(stomp.ConnectionListener):
    def __init__(self, maxlen=100):
        self.messages = deque(maxlen=maxlen)

    def on_error(self, message):  # type: ignore
        print(f"received an error: {message}")

    def on_message(self, message):  # type: ignore
        message_body: dict = json.loads(message.body)
        self.messages.append(message_body)


class RabbitMQMessenger:
    def __init__(
        self,
        host: str | None = None,
        beamline: str | None = None,
        port: int | None = 61613,
        username: str | None = None,
        password: str | None = None,
        destination: Path | list[Path] | str | list[str] | None = None,
        auto_connect: bool = True,
        **kwargs,
    ):
        self.beamline = beamline
        self.host = host
        self.port = port

        if not self.port:
            print("No port specified, defaulting to 61613")
            self.port = 61613

        self.username = username
        self.password = password
        self.auto_connect = auto_connect
        self.destination = destination

        self.default_destination = [
            "/topic/public.worker.event",
            "/topic/gda.messages.scan",
        ]
        # /topic/public.worker.event blueapi
        # defined here https://github.com/DiamondLightSource/blueapi/blob/77129d132d5481b9d6adad3fe15c02d581aff9f7/docs/reference/asyncapi.yaml#L4

        # "/topic/gda.messages.scan"  # nexus file converter
        # defined here: https://gitlab.diamond.ac.uk/daq/d2acq/services/nexus-file-converter/-/blob/master/src/main/resources/application.yaml

        if not self.destination:
            print(f"No destination specified, defaulting to {self.default_destination}")
            self.destination = self.default_destination

        if not self.host and not self.beamline:
            raise ValueError("Either host or beamline must be provided")

        elif not self.host and self.beamline:
            print("Host not specified, constructing from beamline name")
            self.host = f"{self.beamline}-rabbitmq-daq.diamond.ac.uk"

        self.messages = deque()
        self.scan_listener = ScanListener()

        self.run = True

        if self.auto_connect:
            self.setup_connection()
            self.connect()
            self.subscribe()

    def setup_connection(self):
        self.conn = stomp.Connection(
            host_and_ports=[(self.host, self.port)], auto_content_length=False
        )

        self.conn.set_listener("scan_listener", self.scan_listener)

    def connect(self):
        print("Connecting..")

        if self.username and self.password:
            self.conn.connect(self.username, self.password, wait=True)
        else:
            self.conn.connect(wait=True)

        print("Connected to STOMP server at", self.host, self.port)

    def disconnect(self):
        self.conn.disconnect()

    def subscribe(self):
        if isinstance(self.destination, list):
            for i, dest in enumerate(self.destination):
                self.conn.subscribe(destination=dest, id=i + 1, ack="auto")
        else:
            self.conn.subscribe(destination=self.destination, id=1, ack="auto")

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

    def _send_message(self, destination, message):
        self.conn.send(destination=destination, body=message, ack="auto")

    def stop(self):
        self.run = False

    def get_message(self):
        return self.scan_listener.messages.popleft()

    def listen(self, max_iter: int = 50, interval: float | int = 1.0):
        c = 0

        while (self.run is True) and (c < max_iter):
            if self.scan_listener.messages:
                print("Processing message:", self.scan_listener.messages.popleft())
            sleep(interval)
            c += 1


# if __name__ == "__main__":
#     # messenger = RabbitMQMessenger(
#     #     beamline="i22", port=61613, username="guest", password="guest"
#     # )
#     # messenger.listen()

#     m = RabbitMQMessenger(
#         host="i22-control",
#         port=61613,
#         destination=None,
#         auto_connect=True,
#     )
#     m.listen()
