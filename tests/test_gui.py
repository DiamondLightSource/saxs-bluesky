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
    os.environ.__setitem__("DISPLAY", ":0.0")
    os.system("export DISPLAY=:0.0")
    os.system("Xvfb :0.0 &")


def test_panda_gui():
    PandAGUI(configuration=CONFIG.DEFAULT_EXPERIMENT)
