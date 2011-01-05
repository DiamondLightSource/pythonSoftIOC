# Simple example script for building an example soft IOC.

import sys
DEBUG = 'D' in sys.argv[1:]
if DEBUG:
    sys.path.append('/scratch/local/python-debug')
    sys.path.append('/home/mga83/epics/cothread')
    sys.path.append('/home/mga83/epics/iocbuilder')
else:
    import versions

import cothread
from softioc.builder import LoadDatabase

from testing import *
from softioc.softioc import *

LoadDatabase()
iocInit()

interactive_ioc(globals())

