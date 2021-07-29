from softioc import builder, softioc
from softioc.builder import records

builder.SetDeviceName('XX-XX-XX-01')
softioc_record = builder.aOut('VALUE',  initial_value=5)

iocbuilder_record = records.ao("TEST", VAL = 10)
calc = records.calc('CALC', CALC = 'A*B', SCAN = '1 second', INPA = softioc_record, INPB = iocbuilder_record)

builder.LoadDatabase()
softioc.iocInit()

softioc.interactive_ioc(globals())