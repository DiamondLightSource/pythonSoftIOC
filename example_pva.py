from softioc import softioc, builder
from epicsdbbuilder.recordnames import RecordName

builder.SetDeviceName("TC")

record_name = "ENUM"
index = builder.longOut(record_name + ":INDEX", initial_value=1, on_update=print)
index.add_info(
    "Q:group",
    {
        RecordName(record_name): {
            "+id": "epics:nt/NTScalar:1.0",
            "value.foo": {"+type": "structure", "+id": "enum_t"},
            "value.index": {"+type": "plain", "+channel": "VAL", "+putorder": 0},
            "display.description": {"+type": "plain", "+channel": "DESC"},
            "": {"+type": "meta", "+channel": "VAL"},
        }
    },
)

choices = builder.WaveformOut(
    record_name + ":CHOICES",
    initial_value=["ZERO", "ONE", "MANY"],
    FTVL="STRING",
)
choices.add_info(
    "Q:group",
    {
        RecordName(record_name): {
            "+id": "epics:nt/NTEnum:1.0",
            "value.choices": {"+type": "plain", "+channel": "VAL"},
        }
    },
)

builder.LoadDatabase()
softioc.iocInit()
softioc.interactive_ioc(globals())
