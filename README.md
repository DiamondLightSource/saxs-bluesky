[![CI](https://github.com/DiamondLightSource/saxs-bluesky/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/saxs-bluesky/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/saxs-bluesky/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/saxs-bluesky)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# saxs_bluesky

Bluesky plans, plan stubs and utilities for Small Angle Scattering beamline at DLS

This repo is currently designed to work with i22, b21 and will be expanded to work with other beamslines that also use a PandA for hardware triggering. 

Source          | <https://github.com/DiamondLightSource/saxs-bluesky>
:---:           | :---:
Releases        | <https://github.com/DiamondLightSource/saxs-bluesky/releases>

To install saxs-bluesky clone this repo, navigate into the directory containing this repo and install it via:

```
git clone https://github.com/DiamondLightSource/saxs-bluesky.git
cd saxs-bluesky
pip install -e .
```

This module can then be imported and use within your python environment such as:

```python
from saxs_bluesky import __version__

print(f"Hello saxs_bluesky {__version__}")
```

This package can be used within GDA or seperately from GDA. To use it seperately from GDA, (in python3) can be done in the following way:

```python

from saxs_bluesky.utils.profile_groups import Group, Profile

my_profile = Profile(repeats=1,seq_trigger="IMMEDIATE",groups=[]) #currently has no 'groups' - ie line in seq table

#now we create a group
group = Group(
    frames=1,
    trigger="IMMEDIATE"
    wait_time=1,
    wait_units="S",
    run_time=1,
    run_units="S,
    wait_pulses=[0, 0, 0, 0],
    run_pulses=[1, 1, 1, 1],
)

my_profile.append_group(group)

#now we have a profile with a single group. We can add more, delete them and have a look etc

print(my_profile.duration)
print(my_pfoile.total_frames)
```

To use this in an experiment we can do this through the BlueAPIPythonClient, along with the bluesky plans that are loaded in BlueAPI. The BEAMLINE variable should already be set on the beamline, but if not it should be set first.

```python

from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.plans.ncd_panda import configure_panda_triggering, run_panda_triggering

blueapi_config_path = "PATH_TO_CONFIG"

client = BlueAPIPythonClient(BL="i22", blueapi_config_path=blueapi_config_path, instrument_session="cm12345-1")

client.run(
    configure_panda_triggering,
    profile=my_profile,
    detectors=["saxs", "waxs"], #whatever StandardDetectors that are created for the beamline
) #to load all the data onto the panda and the detctors

client.run(run_panda_triggering) #to actually tun the experiment


```

Certain feature can be interacted though the commandline tool, some example commands here. A lot of the configuration can be done through the PandA GUI:

```
python -m saxs-bluesky --version
python -m saxs-bluesky login
python -m saxs-bluesky start_gui
```


If you are operating this repo via the jython terminal and blueAPI then speak to your DAQ person to set it up
