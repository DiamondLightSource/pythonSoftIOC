from argparse import ArgumentParser
from multiprocessing.connection import Client
import sys

from softioc import softioc, builder, pvlog

from conftest import ADDRESS, select_and_recv

if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        import cothread

        # Being run as an IOC, so parse args and set prefix
        parser = ArgumentParser()
        parser.add_argument('prefix', help="The PV prefix for the records")
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        import sim_records

        # Run the IOC
        builder.LoadDatabase()
        softioc.iocInit()

        conn.send("R")  # "Ready"

        select_and_recv(conn, "D")  # "Done"
        # Attempt to ensure all buffers flushed - C code (from `import pvlog`)
        # may not be affected by these calls...
        sys.stdout.flush()
        sys.stderr.flush()

        conn.send("D")  # "Ready"
