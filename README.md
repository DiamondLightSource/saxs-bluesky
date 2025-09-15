[![CI](https://github.com/DiamondLightSource/saxs-bluesky/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/saxs-bluesky/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/saxs-bluesky/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/saxs-bluesky)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# saxs_bluesky

Bluesky plans, plan stubs and utilities for Small Angle Scattering beamline at DLS

This is where you should write a short paragraph that describes what your module does,
how it does it, and why people should use it.

Source          | <https://github.com/DiamondLightSource/saxs-bluesky>
:---:           | :---:
Releases        | <https://github.com/DiamondLightSource/saxs-bluesky/releases>

To install saxs-bluesky clone this repo, navigate into the directory containing this repo and run:

```pip install -e .```

This module can then be imported and use within your python environment such as:

```python
from saxs_bluesky import __version__

print(f"Hello saxs_bluesky {__version__}")
```

Certain feature can be interacted though the commandline tool, some example commands here:

```
python -m saxs-bluesky --version
python -m saxs-bluesky login
python -m saxs-bluesky start_gui
```
