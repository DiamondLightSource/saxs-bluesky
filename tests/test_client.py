import os

from blueapi.client.client import BlueapiClient

import saxs_bluesky.blueapi_configs
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient


def test_blueapi_python_client():
    BL = "i22"

    blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"  # noqa
    CLIENT = BlueAPIPythonClient(BL, blueapi_config_path, "cm12345-1")

    assert isinstance(CLIENT, BlueapiClient)
