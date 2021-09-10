from argparse import ArgumentParser

import asyncio
import time
import sys

from softioc import alarm, softioc, builder, asyncio_dispatcher, pvlog


if __name__ == "__main__":
    # Being run as an IOC, so parse args and set prefix
    parser = ArgumentParser()
    parser.add_argument('prefix', help="The PV prefix for the records")
    parsed_args = parser.parse_args()
    builder.SetDeviceName(parsed_args.prefix)

    import sim_records

    async def callback(value):
        # Set the ao value, which will trigger on_update for it
        sim_records.t_ao.set(value)
        await asyncio.sleep(0.5)
        print("async update %s (%s)" % (value, sim_records.t_ai.get()))
        # Make sure it goes as epicsExit will not flush this for us
        sys.stdout.flush()
        # Set the ai alarm, but keep the value
        sim_records.t_ai.set_alarm(int(value) % 4, alarm.STATE_ALARM)

    # Set a different initial value
    sim_records.t_ai.set(23.45)

    # Create a record to set the alarm
    t_ao = builder.aOut('ALARM', on_update=callback)

    # Run the IOC
    builder.LoadDatabase()
    softioc.iocInit(asyncio_dispatcher.AsyncioDispatcher())
    # Wait for some prints to have happened
    time.sleep(1)
    # Make sure coverage is written on epicsExit
    from pytest_cov.embed import cleanup
    sys._run_exitfuncs = cleanup
    softioc.interactive_ioc()
