# Simple example script for building an example soft IOC.

import versions
from softioc import *
from builder import LoadDatabase

from testing import *

LoadDatabase()
iocInit()

from numpy import *
def t(x=1, d=float):
    t_waveform_out.set(x*ones(wf_len, dtype=d))

interactive_ioc(globals())

