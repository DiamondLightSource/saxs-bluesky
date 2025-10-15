import os

from blueapi.client.client import BlueapiClient

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient


def test_blueapi_python_client():
    beamline = "i22"

    blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{beamline}_blueapi_config.yaml"  # noqa
    client = BlueAPIPythonClient(beamline, blueapi_config_path, "cm12345-1")

    assert isinstance(client, BlueapiClient)


def test_blueapi_python_client_change_session():
    beamline = "i22"
    blueapi_config_path = (
        f"./src/saxs_bluesky/blueapi_configs/{beamline}_blueapi_config.yaml"
    )
    client = BlueAPIPythonClient(beamline, blueapi_config_path, "None")

    assert client.beamline == "i22"
    client.change_session("9999")
    assert client.instrument_session == "9999"
