from softioc import autosave, builder, softioc
import cothread

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create records, set some of them to autosave, also save some of their fields

builder.aOut("AO", autosave=True)
builder.aIn("AI", autosave_fields=["PREC", "SCAN"])
builder.boolIn("BO")
builder.WaveformIn("WAVEFORMOUT", [0, 0, 0, 0], autosave=True)
minutes = builder.longOut("MINUTESRUN", autosave=True)

autosave.configure(
    directory="/tmp/autosave-data/MY-DEVICE-PREFIX",
    name="MY-DEVICE-PREFIX",
    save_period=20.0
)

builder.LoadDatabase()
softioc.iocInit()

# Start processes required to be run after iocInit
def update():
    while True:
        cothread.Sleep(60)
        minutes.set(minutes.get() + 1)

cothread.Spawn(update)

softioc.interactive_ioc(globals())
