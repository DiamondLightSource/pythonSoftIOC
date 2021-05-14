from argparse import ArgumentParser

import asyncio
import time
import sys

from softioc import softioc, builder, device, pvlog


if __name__ == "__main__":
    # Being run as an IOC, so parse args and set prefix
    parser = ArgumentParser()
    parser.add_argument('prefix', help="The PV prefix for the records")
    parsed_args = parser.parse_args()
    builder.SetDeviceName(parsed_args.prefix)

    import sim_records

    async def callback(value):
        await asyncio.sleep(0.5)
        print("async update %s" % value)
        sim_records.t_ai.set(value)

    t_ao = builder.aOut('AO2', initial_value=12.45, on_update=callback)

    device.use_asyncio()

    # Run the IOC
    builder.LoadDatabase()
    softioc.iocInit()
    # Wait for some prints to have happened
    time.sleep(1)
    # Make sure coverage is written on epicsExit
    from pytest_cov.embed import cleanup
    sys.exitfunc = cleanup
    softioc.interactive_ioc()
