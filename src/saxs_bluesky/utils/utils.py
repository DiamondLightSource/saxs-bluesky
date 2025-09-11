import os
from importlib import import_module
from pathlib import Path

############################################################################################
import matplotlib.pyplot as plt
import numpy as np
from dodal.utils import get_beamline_name

import saxs_bluesky.beamline_configs
from saxs_bluesky.utils.ncdcore import ncdcore
from saxs_bluesky.utils.profile_groups import ExperimentLoader, Profile


def get_saxs_beamline() -> str:
    BL = get_beamline_name(os.getenv("BEAMLINE"))  # type: ignore

    if BL is None:
        BL = "i22"
        os.environ["BEAMLINE"] = BL

    return BL


BL = get_saxs_beamline()


def load_beamline_config():
    BL_CONFIG = import_module(f"{saxs_bluesky.beamline_configs.__name__}.{BL}_config")
    return BL_CONFIG


class ProfilePlotter:
    @staticmethod
    def generate_pulse_signal(
        profile: Profile, pulse: int
    ) -> tuple[np.ndarray, np.ndarray]:
        current_time = 0.0
        trigger_time = [current_time]
        signal = [0]  # starts low and ends low

        for group in profile.groups:
            wait_active = group.wait_pulses[pulse]
            run_active = group.run_pulses[pulse]

            for _frame in range(group.frames):
                current_time += group.wait_time * ncdcore.to_seconds(group.wait_units)
                trigger_time.append(current_time)
                signal.append(wait_active)

                current_time += group.run_time * ncdcore.to_seconds(group.run_units)
                trigger_time.append(current_time)
                signal.append(run_active)

        trigger_time.append(current_time + (current_time) / 10)
        signal.append(0)  # starts low and ends low

        trigger_time = np.asarray(trigger_time)
        signal = np.asarray(signal)

        return trigger_time, signal

    def plot_pulses(self):
        if len(self.profile.active_pulses) != len(self.axes):
            plt.close()
            self.setup_figure()

        if len(self.profile.active_pulses) > 0:
            for n, i in enumerate(self.profile.active_pulses):
                trigger_time, signal = ProfilePlotter.generate_pulse_signal(
                    self.profile, i - 1
                )

                if self.axes[n].has_data():
                    self.axes[n].clear()

                self.axes[n].step(trigger_time, signal)
                self.axes[n].set_ylabel(f"{self.pulse_names[n]} Signal")  # type: ignore

        self.fig.canvas.draw()

    def on_close(self, event):
        print("Figure Closed")
        plt.clf()
        plt.close()
        self.open = False

    def show(self, block=False):
        # plt.tight_layout(pad=1.15)
        self.open = True
        plt.xlabel("Time (s)")
        plt.show(block=block)

    def setup_figure(self):
        self.fig, self.axes = plt.subplots(
            len(self.profile.active_pulses),
            1,
            sharex=True,
            figsize=(8, len(self.profile.active_pulses) * 3),
            num=self.name,
        )

        self.fig.canvas.mpl_connect("close_event", self.on_close)

    def __init__(self, profile: Profile, pulse_names: list[str] | None = None):
        self.profile = profile
        self.pulse_names = pulse_names
        self.name = "Panda Pulse Signals"
        self.open = False

        if self.pulse_names is None:
            self.pulse_names = [
                f"Seq Pulse {f}" for f in range(len(self.profile.active_pulses))
            ]

        self.setup_figure()


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).parent.parent.parent.parent

    default_config_path = os.path.join(
        _REPO_ROOT, "src/saxs_bluesky/profile_yamls", "panda_config.yaml"
    )

    experimental_profiles = ExperimentLoader.read_from_yaml(default_config_path)
    profile = experimental_profiles.profiles[0]

    plotter = ProfilePlotter(profile)
    plotter.plot_pulses()
