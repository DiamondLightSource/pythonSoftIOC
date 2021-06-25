# Import the basic framework components.
from softioc import softioc, builder
import cothread

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create some records
ai = builder.aIn('AI', initial_value=5)
ao = builder.aOut('AO', initial_value=12.45, on_update=lambda v: ai.set(v))

# Boilerplate get the IOC started
builder.LoadDatabase()
softioc.iocInit()

# Start processes required to be run after iocInit
def update():
    while True:
        ai.set(ai.get() + 1)
        cothread.Sleep(1)


cothread.Spawn(update)

# Finally leave the IOC running with an interactive shell.
softioc.interactive_ioc(globals())
