import subprocess
import sys

from saxs_bluesky import __version__
from saxs_bluesky.__main__ import login, main


def test_cli_version():
    cmd = [sys.executable, "-m", "saxs_bluesky", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__


def test_main():
    main()


def test_login():
    login()
