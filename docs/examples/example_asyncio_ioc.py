# Import the basic framework components.
from softioc import softioc, builder
from aioca import caget, caput
import asyncio

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create some records
ai = builder.aIn('AI', initial_value=5)

def update(val):
    print("got here")
    print(val)
    ai.set(val)

ao = builder.aOut('AO', initial_value=12.45, on_update=update)

# Boilerplate get the IOC started
builder.LoadDatabase()
softioc.iocInit()

# Perform some reading/writing to the PVs
async def do_read_write():
    print(await caget("MY-DEVICE-PREFIX:AO"))
    print(await caget("MY-DEVICE-PREFIX:AI"))
    await caput("MY-DEVICE-PREFIX:AO", "999")
    await asyncio.sleep(10)
    print(await caget("MY-DEVICE-PREFIX:AI"))
    print(await caget("MY-DEVICE-PREFIX:AO"))

#asyncio.run(do_read_write())

print(asyncio.run(caget("MY-DEVICE-PREFIX:AI")))
print(asyncio.run(caget("MY-DEVICE-PREFIX:AO")))
print(asyncio.run(caput("MY-DEVICE-PREFIX:AO","999")))

print(asyncio.run(caget("MY-DEVICE-PREFIX:AI")))
print(asyncio.run(caget("MY-DEVICE-PREFIX:AO")))


softioc.interactive_ioc(globals())
