import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Pick one as the "default" for type hints
    from saxs_bluesky.beamline_configs.i22_config import *  # noqa


beamline = os.environ.get("BEAMLINE")

if beamline is None:
    raise ValueError("BEAMLINE variable must be set!")

try:
    module_name = f"saxs_bluesky.beamline_configs.{beamline.lower()}_config"
    module = __import__(module_name, fromlist=["*"])
    # Copy everything from the real module
    for name, value in vars(module).items():
        if not name.startswith("_"):
            globals()[name] = value
except ValueError as e:
    print(
        e,
        f"Unsupported BEAMLINE: {beamline}. Add {beamline}_config.py to beamline_configs",  # noqa
    )
