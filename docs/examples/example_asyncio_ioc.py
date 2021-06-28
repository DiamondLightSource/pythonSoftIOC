# Import the basic framework components.
import atexit
from softioc import softioc, builder
from aioca import caget, caput, _catools
import asyncio

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create some records
ai = builder.aIn('AI', initial_value=5)

async def update(val):
    ai.set(val)

ao = builder.aOut('AO', initial_value=12.45, on_update=update)

# Boilerplate get the IOC started
builder.LoadDatabase()
softioc.iocInit()

# Perform some reading/writing to the PVs
async def do_read_write():
    ai_val = await caget("MY-DEVICE-PREFIX:AI")
    await caput("MY-DEVICE-PREFIX:AO", "999")


asyncio.run(do_read_write())


