from softioc import autosave, builder, softioc
import cothread

# Set the record prefix
builder.SetDeviceName("MY-DEVICE-PREFIX")

# Create records, set some of them to autosave, also save some of their fields

builder.aOut("AO", autosave=True)
builder.aIn("AI", autosave_fields=["PREC", "EGU"])
builder.boolIn("BO")
builder.WaveformIn("WAVEFORMIN", [0, 0, 0, 0], autosave=True)
with autosave.Autosave(True, ["LOPR", "HOPR"]):
    builder.aOut("AUTOMATIC-AO", autosave_fields=["EGU"])
seconds = builder.longOut("SECONDSRUN", autosave=True)

autosave.configure(
    directory="/tmp/autosave-data",
    name="MY-DEVICE-PREFIX",
    save_period=5.0
)

builder.LoadDatabase()
softioc.iocInit()

# Start processes required to be run after iocInit
def update():
    while True:
        cothread.Sleep(1)
        seconds.set(seconds.get() + 1)

cothread.Spawn(update)

softioc.interactive_ioc(globals())
