# Import the basic framework components.
from softioc import softioc, builder, asyncio_dispatcher
import asyncio

# Create an asyncio dispatcher, the event loop is now running
dispatcher = asyncio_dispatcher.AsyncioDispatcher()

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create some records
ai = builder.aIn('AI', initial_value=5)
ao = builder.aOut('AO', initial_value=12.45, always_update=True,
                  on_update=lambda v: ai.set(v))

# Boilerplate get the IOC started
builder.LoadDatabase()
softioc.iocInit(dispatcher)

# Start processes required to be run after iocInit
async def update():
    while True:
        ai.set(ai.get() + 1)
        await asyncio.sleep(1)

asyncio.run_coroutine_threadsafe(update(), dispatcher.loop)

# Finally leave the IOC running with an interactive shell.
softioc.interactive_ioc(globals())
