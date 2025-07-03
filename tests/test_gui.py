import os

from sas_bluesky.panda_gui import PandAGUI


def test_panda_gui():
    os.environ["DISPLAY"] = 0.0
    PandAGUI(start=False)
