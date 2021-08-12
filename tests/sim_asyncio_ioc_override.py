from argparse import ArgumentParser

import asyncio
import os
import re
from pathlib import Path

from softioc import softioc, builder, asyncio_dispatcher


if __name__ == "__main__":
    # Being run as an IOC, so parse args and set prefix
    parser = ArgumentParser()
    parser.add_argument('prefix', help="The PV prefix for the records")
    parsed_args = parser.parse_args()
    builder.SetDeviceName(parsed_args.prefix)

    # Load the base records without DTYP fields
    macros = dict(device=parsed_args.prefix)
    with open(Path(__file__).parent / "hw_records.db") as f:
        for line in f.readlines():
            if not re.match(r"\s*field\s*\(\s*DTYP", line):
                builder.AddDatabaseLine(line, macros)

    # Override DTYPE and OUT, and provide a callback
    gain = builder.boolOut("GAIN", on_update=print)

    # Run the IOC
    builder.LoadDatabase()
    event_loop = asyncio.get_event_loop()
    softioc.iocInit(asyncio_dispatcher.AsyncioDispatcher(event_loop))
    event_loop.run_forever()
