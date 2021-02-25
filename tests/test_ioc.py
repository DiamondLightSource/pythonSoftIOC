# Simple example script for building an example soft IOC.

import cothread
from softioc import softioc, builder, pvlog

from sim_records import *

softioc.devIocStats('TS-DI-TEST-01')

builder.LoadDatabase()
softioc.iocInit()

softioc.interactive_ioc(globals())
