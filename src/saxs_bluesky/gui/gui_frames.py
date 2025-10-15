import tkinter
from tkinter import ttk

from dodal.common import inject


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
