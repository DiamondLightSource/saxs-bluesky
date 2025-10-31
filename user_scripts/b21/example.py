from saxs_bluesky.beamline_configs.b21_config import CLIENT
from saxs_bluesky.plans.ncd_panda import (
    configure_panda_triggering,
    run_panda_triggering,
)
from saxs_bluesky.utils.plotter import ProfilePlotter
from saxs_bluesky.utils.profile_groups import Group, Profile

my_profile = Profile(
    repeats=1, groups=[]
)  # currently has no 'groups' - ie line in seq table

# now we create a group
group = Group(
    frames=1,
    trigger="IMMEDIATE",
    wait_time=10,
    wait_units="MS",
    run_time=1,
    run_units="S",
    wait_pulses=[1, 0, 0, 0],
    run_pulses=[1, 1, 1, 1],
)

my_profile.append_group(group)

# now we have a profile with a single group. We can add more
# delete them and have a look
print(f"Duration of profile: {my_profile.duration} seconds")
print(f"Number of frames: {my_profile.total_frames}")


plotter = ProfilePlotter(my_profile)
plotter.plot_pulses()
plotter.show()


CLIENT.change_session(
    "cm40642-5"
)  # defaults to commissioning. Change the instrument session to your experiment

CLIENT.run(
    configure_panda_triggering,
    profile=my_profile,
    detectors=[
        "saxs",
        "waxs",
        "it",
        "i0",
    ],  # whatever StandardDetectors that are created for the beamline
)  # to load all the data onto the panda and the detctors

CLIENT.run(run_panda_triggering)  # to actually tun the experiment
