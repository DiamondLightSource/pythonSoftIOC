# Simple example script for building an example soft IOC.

import versions

import cothread
from softioc import softioc, builder, pvlog

from testing import *

builder.LoadDatabase()
softioc.iocInit()

softioc.interactive_ioc(globals())
