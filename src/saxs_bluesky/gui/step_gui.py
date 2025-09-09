import tkinter

from dodal.common import inject

from saxs_bluesky.gui.gui_utils import LabelEntryPair
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

BL = get_saxs_beamline()
CONFIG = load_beamline_config(BL)


class StepWidget:
    def step_action(self):
        params = {
            "start": float(self.StartLabelEntry.get_value()),
            "stop": float(self.StopLabelEntry.get_value()),
            "num": float(self.StepLabelEntry.get_value()),
            "axis": inject(self.ScanAxisLabelEntry.get_value()),
            "detectors": list(CONFIG.FAST_DETECTORS),
        }

        try:
            self.client.run("step_scan", params)
        except ConnectionError:
            print("Could not upload profile to panda")

    def rstep_action(self):
        params = {
            "start": float(self.StartLabelEntry.get_value()),
            "stop": float(self.StopLabelEntry.get_value()),
            "num": float(self.StepLabelEntry.get_value()),
            "axis": inject(self.ScanAxisLabelEntry.get_value()),
            "detectors": list(CONFIG.FAST_DETECTORS),
        }

        try:
            self.client.run("step_rscan", params)
        except ConnectionError:
            print("Could not upload profile to panda")

    def show(self):
        print(self.StartLabelEntry.get_value())

    def __init__(self, instrument_session):
        blueapi_config_path = (
            f"./src/saxs_bluesky/blueapi_configs/{BL}_blueapi_config.yaml"
        )

        self.instrument_session = instrument_session

        self.client = BlueAPIPythonClient(
            BL, blueapi_config_path, self.instrument_session
        )

        self.root = tkinter.Tk()
        self.root.minsize(300, 160)
        self.root.title("Step Scan Control")

        # ttk.Label(self.root, text="Start").grid(
        #     column=0, row=0, padx=5, pady=5, sticky="w"
        # )
        # ttk.Label(self.root, text="Stop").grid(
        #     column=0, row=1, padx=5, pady=5, sticky="w"
        # )
        # ttk.Label(self.root, text="Step").grid(
        #     column=0, row=2, padx=5, pady=5, sticky="w"
        # )

        self.StartLabelEntry = LabelEntryPair(
            master=self.root, label_text="Start", row=0, column=1, initial_val="0"
        )
        self.StopLabelEntry = LabelEntryPair(
            master=self.root, label_text="Stop", row=1, column=1, initial_val="0"
        )
        self.StepLabelEntry = LabelEntryPair(
            master=self.root, label_text="Num", row=2, column=1, initial_val="0"
        )

        self.ScanAxisLabelEntry = LabelEntryPair(
            master=self.root,
            label_text="Scan Axis",
            row=3,
            column=1,
            initial_val="base_top.x",
        )

        tkinter.Button(self.root, text="Run Step Scan", command=self.step_action).grid(
            row=4, column=1, padx=5, pady=5, sticky="w"
        )

        tkinter.Button(
            self.root, text="Run RStep Scan", command=self.rstep_action
        ).grid(row=4, column=2, padx=5, pady=5, sticky="w")

        self.root.mainloop()


if __name__ == "__main__":
    StepWidget("None")
