import subprocess
import sys

from softioc import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "softioc", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
