from softioc import builder, softioc
from softioc.builder import records

builder.SetDeviceName("XX-XX-XX-01")

py_record = builder.aOut("VAL1", initial_value=5, on_update=print)
soft_record = records.ao("VAL2", VAL=10)

calc = records.calc("CALC", CALC="A*B", INPA=builder.CP(py_record), B=1)

soft_record.OUT = builder.PP(calc.B)

builder.LoadDatabase()
softioc.iocInit()

softioc.interactive_ioc(globals())
