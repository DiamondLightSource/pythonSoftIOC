import os
import sys
from argparse import ArgumentParser

from softioc import __version__


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("script", help="The python script to run")
    parsed_args = parser.parse_args(args)
    # Insert the directory containing script onto the path in case we do
    # any imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(parsed_args.script)))
    if sys.version_info < (3, 0):
        # Python 2
        execfile(parsed_args.script)
    else:
        # Python 3
        exec(open(parsed_args.script).read())


if __name__ == "__main__":
    main()
