import os
import sys
from argparse import ArgumentParser
import subprocess

from softioc import __version__


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("script", help="The python script to run")
    parser.add_argument(
        "arg", help="Any arguments to pass to the script", nargs="*")
    parsed_args = parser.parse_args(args)
    # Execute as subprocess
    cmd = [sys.executable, parsed_args.script, *parsed_args.arg]
    subprocess.Popen(cmd).communicate()


if __name__ == "__main__":
    main()
