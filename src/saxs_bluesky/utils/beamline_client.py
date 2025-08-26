from pathlib import Path

from blueapi.client.client import BlueapiClient
from blueapi.config import (
    ApplicationConfig,
    ConfigLoader,
)


def blueapi_beamline_client_loader(BL: str):
    blueapi_config_path = Path(
        f"./src/saxs_bluesky/blueapi_configs/{BL}_blueapi_config.yaml"
    )
    config_loader = ConfigLoader(ApplicationConfig)
    config_loader.use_values_from_yaml(blueapi_config_path)
    loaded_config = config_loader.load()
    client = BlueapiClient.from_config(loaded_config)

    return client
