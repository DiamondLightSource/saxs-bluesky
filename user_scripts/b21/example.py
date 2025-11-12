import numpy as np
from dodal.plan_stubs.wrapped import (
    move,
    move_relative,
    set_absolute,
    set_relative,
    sleep,
)

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
    ],  # whatever StandardDetectors that are created for the beamline
)  # to load all the data onto the panda and the detctors

CLIENT.run(run_panda_triggering)  # to actually tun the experiment


#########################

print(CLIENT.show_devices())  # to show what devices are available for your beamline
print(CLIENT.show_plans())  # to show what plans are available


CLIENT.run(move, moves={"table.x": 1})  # move table.x to 1

xs = np.arange(0, 0.5, 0.1)  # [0. 0.1 0.2 0.3 0.4]
ys = np.arange(-9.5, -10, -0.1)  # [-9.5 -9.6 -9.7 -9.8 -9.9]

print(xs, ys)

for x, y in zip(xs, ys, strict=True):
    CLIENT.run(move, moves={"table.x": x, "table.y": y})  # move table to x, y
    CLIENT.run(sleep, time=1)  # sleep for 1 second


CLIENT.run(move, moves={"table.x": 0})  # move table.x to 0
CLIENT.run(sleep, time=1)  # sleep for 1 second

for _ in range(5):
    CLIENT.run(move_relative, moves={"table.x": 0.1})  # increase by +0.1 each time
    CLIENT.run(sleep, time=1)  # sleep for 1 second
    # so by the end table.x is at 0.5 again

CLIENT.run(set_absolute, movable="table.x", value=0.1)  # set_abs to 0.1
CLIENT.run(set_relative, movable="table.x", value=0.1)  # set_relaticve by +0.1
# So table.x ends at 0.2
