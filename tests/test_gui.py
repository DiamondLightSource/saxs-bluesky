from saxs_bluesky.gui.panda_gui import PandAGUI
from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

############################################################################################

BL = get_saxs_beamline()
CONFIG = load_beamline_config()


def test_panda_gui():
    PandAGUI(configuration=CONFIG.DEFAULT_EXPERIMENT)
