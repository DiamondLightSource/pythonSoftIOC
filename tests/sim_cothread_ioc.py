from argparse import ArgumentParser
from multiprocessing.connection import Client
import sys

from softioc import softioc, builder, pvlog

from conftest import ADDRESS, log, select_and_recv

if __name__ == "__main__":
    log("sim_cothread_ioc starting")
    with Client(ADDRESS) as conn:
        import cothread

        # Being run as an IOC, so parse args and set prefix
        parser = ArgumentParser()
        parser.add_argument('prefix', help="The PV prefix for the records")
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        import sim_records

        log("sim_cothread_ioc records created")

        # Run the IOC
        builder.LoadDatabase()
        softioc.iocInit()

        log("sim_cothread_ioc ready")

        conn.send("R")  # "Ready"

        log("sim_cothread_ioc waiting for Done")

        select_and_recv(conn, "D")  # "Done"
        # Attempt to ensure all buffers flushed - C code (from `import pvlog`)
        # may not be affected by these calls...
        sys.stdout.flush()
        sys.stderr.flush()

        log("sim_cothread_ioc sending Done")

        conn.send("D")  # "Ready"
