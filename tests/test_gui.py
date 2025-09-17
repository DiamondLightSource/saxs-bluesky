import os

from saxs_bluesky.gui.panda_gui import PandAGUI
from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

############################################################################################

BL = get_saxs_beamline()
CONFIG = load_beamline_config()


if os.environ.get("DISPLAY", "") == "":
    print("no display found. Using :0.0")
    os.environ.__setitem__("DISPLAY", ":0.0")


def test_panda_gui():
    CONFIG = load_beamline_config()
    PandAGUI(configuration=CONFIG.DEFAULT_EXPERIMENT, start=False)
