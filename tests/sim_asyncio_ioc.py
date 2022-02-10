import asyncio
import sys

from argparse import ArgumentParser
from multiprocessing.connection import Client

from softioc import alarm, softioc, builder, asyncio_dispatcher, pvlog

from conftest import ADDRESS, select_and_recv

if __name__ == "__main__":
    # Being run as an IOC, so parse args and set prefix
    parser = ArgumentParser()
    parser.add_argument('prefix', help="The PV prefix for the records")
    parsed_args = parser.parse_args()
    builder.SetDeviceName(parsed_args.prefix)

    import sim_records

    with Client(ADDRESS) as conn:

        async def callback(value):
            # Set the ao value, which will trigger on_update for it
            sim_records.t_ao.set(value)
            print("async update %s (%s)" % (value, sim_records.t_ai.get()))
            # Make sure it goes as epicsExit will not flush this for us
            sys.stdout.flush()
            # Set the ai alarm, but keep the value
            sim_records.t_ai.set_alarm(int(value) % 4, alarm.STATE_ALARM)
            # Must give the t_ai record time to process
            await asyncio.sleep(1)
            conn.send("C")  # "Complete"

        # Set a different initial value
        sim_records.t_ai.set(23.45)

        # Create a record to set the alarm
        t_ao = builder.aOut('ALARM', on_update=callback)

        # Run the IOC
        builder.LoadDatabase()
        softioc.iocInit(asyncio_dispatcher.AsyncioDispatcher())

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
