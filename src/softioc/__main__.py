import os
import sys
from argparse import ArgumentParser
import subprocess

from . import __version__


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "script", help="The python script to run", nargs="?", default=None)
    parser.add_argument(
        "arg", help="Any arguments to pass to the script", nargs="*")
    parsed_args, unknown = parser.parse_known_args(args)

    # Execute as subprocess.
    cmd = [sys.executable] + parsed_args.arg + unknown
    if parsed_args.script:
        cmd.insert(1, parsed_args.script)

    subprocess.Popen(cmd).communicate()


if __name__ == "__main__":
    main()
