# Simple example script for building an example soft IOC.

import versions
from softioc import *
from builder import LoadDatabase

from testing import *

LoadDatabase()
iocInit()

interactive_ioc(globals())

