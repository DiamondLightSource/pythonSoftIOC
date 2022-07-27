import asyncio
import os
import re
import sys

from pathlib import Path
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser
from multiprocessing.connection import Client
import threading

from softioc import softioc, builder, asyncio_dispatcher

from conftest import ADDRESS, select_and_recv

if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        # Being run as an IOC, so parse args and set prefix
        parser = ArgumentParser()
        parser.add_argument('prefix', help="The PV prefix for the records")
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        # Load the base records without DTYP fields
        with open(Path(__file__).parent / "hw_records.db", "rb") as inp:
            with NamedTemporaryFile(suffix='.db', delete=False) as out:
                for line in inp.readlines():
                    if not re.match(rb"\s*field\s*\(\s*DTYP", line):
                        out.write(line)
        softioc.dbLoadDatabase(
            out.name, substitutions=f"device={parsed_args.prefix}")
        os.unlink(out.name)

        # Override DTYPE and OUT, and provide a callback
        gain = builder.boolOut("GAIN", on_update=print)
        softioc.devIocStats(parsed_args.prefix)

        # Run the IOC
        builder.LoadDatabase()
        event_loop = asyncio.get_event_loop()
        worker = threading.Thread(target=event_loop.run_forever)
        worker.daemon = True
        worker.start()
        softioc.iocInit(asyncio_dispatcher.AsyncioDispatcher(event_loop))

        conn.send("R")  # "Ready"

        # Make sure coverage is written on epicsExit
        from pytest_cov.embed import cleanup
        sys._run_exitfuncs = cleanup

        select_and_recv(conn, "D")  # "Done"
        # Attempt to ensure all buffers flushed - C code (from `import pvlog`)
        # may not be affected by these calls...
        sys.stdout.flush()
        sys.stderr.flush()

        conn.send("D")  # "Done"
