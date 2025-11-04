import subprocess
import sys

import saxs_bluesky.__main__
from saxs_bluesky import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "saxs_bluesky", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__


def test_main():
    filepath = (saxs_bluesky.__main__).__file__

    with open(filepath) as f:
        code = f.read()

    exec(code)
