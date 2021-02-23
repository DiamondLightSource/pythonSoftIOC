# Simple example script for building an example soft IOC.

import versions

import cothread
from softioc import softioc, builder, pvlog

from testing import *

softioc.devIocStats('TS-DI-TEST-01')

builder.LoadDatabase()
softioc.iocInit()

softioc.interactive_ioc(globals())
