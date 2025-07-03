import os
from importlib import import_module
from pathlib import Path

############################################################################################
import matplotlib.pyplot as plt
import numpy as np
from dodal.utils import get_beamline_name

from sas_bluesky.profile_groups import ExperimentProfiles, Profile
from sas_bluesky.utils.ncdcore import ncdcore


def get_sas_beamline() -> str:
    BL = get_beamline_name(os.getenv("BEAMLINE"))  # type: ignore

    if BL is None:
        BL = "i22"
        os.environ["BEAMLINE"] = BL

    return BL


BL = get_sas_beamline()


def load_beamline_config():
    BL_CONFIG = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_config")
    return BL_CONFIG


def load_beamline_profile():
    BL_PROF = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_profile")
    return BL_PROF


def load_beamline_devices():
    BL_DEV = import_module(f"sas_bluesky.defaults_configs.{BL}.{BL}_dev")
    return BL_DEV


def generate_pulse_signal(profile: Profile, pulse: int):
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


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).parent.parent.parent.parent

    default_config_path = os.path.join(
        _REPO_ROOT, "src/sas_bluesky/profile_yamls", "panda_config.yaml"
    )

    experimental_profiles = ExperimentProfiles.read_from_yaml(default_config_path)

    trigger_time, signal = generate_pulse_signal(experimental_profiles.profiles[1], 1)

    plt.step(trigger_time, signal)
    plt.show()
