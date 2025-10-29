import tkinter
from itertools import product
from tkinter import ttk

from bluesky.plans import count
from dodal.common import inject

from saxs_bluesky.gui.step_gui import StepWidget
from saxs_bluesky.logging.bluesky_logpanel import BlueskyLogPanel
from saxs_bluesky.plans.ncd_panda import log_detectors, set_detectors
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient

ROWS = range(0, 10, 2)
COLS = range(0, 6, 2)
ROW_COL = product(ROWS, COLS)


class ActiveDetectorsFrame(ttk.Frame):
    def __init__(
        self, window, pulse_blocks, pulse_connections, active_detectors, *args, **kwargs
    ):
        self.window = window
        self.pulse_blocks = pulse_blocks
        self.pulse_connections = pulse_connections
        self.active_detectors = active_detectors

        super().__init__(self.window, *args, **kwargs)

        self.pulse_frame = ttk.Frame(self.window, borderwidth=5)
        self.pulse_frame.pack(fill="both", side="bottom", expand=True)

        out_label = ttk.Label(self.pulse_frame, text="Enable Device")
        out_label.pack(fill="both", side="top", expand=True)
        self.build_active_detectors_frame()

    def build_active_detectors_frame(self):
        self.active_detectors_dict = {}

        for pulse in range(self.pulse_blocks):
            active_detectors_frame_n = ttk.Frame(
                self.pulse_frame, borderwidth=5, relief="raised"
            )

            active_detectors_frame_n.pack(
                fill="both", expand=True, side="left", anchor="w"
            )

            pulse_label = ttk.Label(
                active_detectors_frame_n, text=f"Pulse Group: {pulse}"
            )

            pulse_label.grid(column=0, row=0, padx=5, pady=5, sticky="w")

            # if pulse == 0:
            ttl_label = ttk.Label(active_detectors_frame_n, text="TTL:")
            ttl_label.grid(column=0, row=1, padx=5, pady=5, sticky="w")

            for n, det in enumerate(self.pulse_connections[pulse + 1]):
                # experiment_var=tkinter.StringVar(value=self.configuration.experiment)

                if det is None:
                    det = ""

                var = tkinter.IntVar()

                if (det.lower() == "fs") or ("shutter" in det.lower()):
                    var.set(1)
                    ad_entry = ttk.Checkbutton(
                        active_detectors_frame_n,
                        text=det,
                        state="disabled",
                        variable=var,
                    )
                else:
                    ad_entry = ttk.Checkbutton(
                        active_detectors_frame_n,
                        text=det,
                        variable=var,
                    )

                if det in self.active_detectors:
                    var.set(1)

                ad_entry.grid(column=n + 1, row=1, padx=5, pady=5, sticky="w")

                if det.lower() != "fs":
                    self.active_detectors_dict[det] = var

    def get_active_detectors(self):
        active_detectors = []

        for det in self.active_detectors_dict.keys():
            if self.active_detectors_dict[det].get() == 1:
                active_detectors.append(inject(det))

        return active_detectors


class ClientControlPanel:
    def __init__(
        self, beamline: str, client: BlueAPIPythonClient, get_active_detectors
    ):
        self.beamline = beamline
        self.get_active_detectors = get_active_detectors
        self.window = tkinter.Tk()
        self.client: BlueAPIPythonClient = client

        self.window.minsize(400, 300)
        self.window.title("Client Control Panel")

        self.build_dev_frame()

    def build_dev_frame(self):
        self.run_frame = ttk.Frame(self.window, borderwidth=5)

        self.run_frame.pack(fill="y", expand=True, side="right")

        row_col = next(ROW_COL)
        ttk.Button(self.run_frame, text="Get Plans", command=self.get_plans).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(self.run_frame, text="Get Devices", command=self.get_devices).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(self.run_frame, text="Stop Plan", command=self.client.stop).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(self.run_frame, text="Pause Plan", command=self.client.pause).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(self.run_frame, text="Resume Plan", command=self.client.resume).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame, text="Reload Env", command=self.client.reload_environment
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        ######################################################################
        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame, text="Set dets", command=self.set_detectors_plan
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame, text="Log dets", command=self.log_detectors_plan
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )
        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame, text="Open Step Widget", command=self.open_step_widget
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame, text="Count Detector", command=self.count_detectors
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame,
            text="Show Active Dets",
            command=self.show_active_detectors,
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        row_col = next(ROW_COL)
        ttk.Button(
            self.run_frame,
            text="Open Log Panel",
            command=self.open_log_panel,
        ).grid(
            row=row_col[0],
            column=row_col[1],
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        return None

    def get_plans(self):
        plans = self.client.get_plans().plans

        for plan in plans:
            print(plan.name, "\n")

    def get_devices(self):
        devices = self.client.get_devices().devices

        for dev in devices:
            print(dev, "\n\n")

    def log_detectors_plan(self):
        try:
            self.client.run(log_detectors)
        except ConnectionError:
            print("Could not upload profile to panda")

    def count_detectors(self):
        try:
            self.client.run(
                count,
                detectors=list(self.get_active_detectors()),
            )
        except ConnectionError:
            print("Could not upload profile to panda")

    def open_step_widget(self):
        StepWidget(list(self.get_active_detectors()), self.client)

    def open_log_panel(self):
        BlueskyLogPanel(beamline=self.beamline)

    def show_active_detectors(self):
        active_detectors = self.get_active_detectors()
        print(active_detectors)

    def set_detectors_plan(self):
        try:
            self.client.run(
                set_detectors,
                detectors=list(self.get_active_detectors()),
                timeout=1,
            )
        except ConnectionError:
            print("Could not upload profile to panda")
