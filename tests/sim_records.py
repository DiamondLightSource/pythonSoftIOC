# Simple script for build a set of test PVs.

from __future__ import print_function

from epicsdbbuilder import GetRecordNames, WriteRecords

from softioc import softioc, alarm
from softioc.builder import *

import numpy

names = GetRecordNames()
if names.prefix:
    ioc_name = names.prefix[0]
else:
    ioc_name = 'TS-DI-TEST-01'
    SetDeviceName(ioc_name)

def on_update(value):
    print('on_update', repr(value))

def on_update_name(value, name):
    print('on_update', name, ':', repr(value))

# The publicly accessible records.
t_ai = None
t_ao = None

def create_records():
    global t_ai, t_ao

    t_ai = aIn('AI', initial_value=12.34)

    boolIn('BOOLIN', 'True', 'False', initial_value=False)
    longIn('LONGIN', initial_value=33)
    stringIn('STRINGIN', initial_value="Testing string")
    mbbIn(
        'MBBI', ('One', alarm.MAJOR_ALARM), 'Two', ('Three', "MINOR"),
        initial_value=2)

    t_ao = aOut('AO', initial_value=12.45, on_update_name=on_update_name)

    boolOut('BOOLOUT', 'Zero', 'One', initial_value=True, on_update=on_update)
    longOut('LONGOUT', initial_value=2008, on_update=on_update)
    stringOut('STRINGOUT', initial_value='watevah', on_update=on_update)
    mbbOut('MBBO', 'Ein', 'Zwei', 'Drei', initial_value=1)

    def update_sin_wf(value):
        print('update_sin_wf', value)
        sin_wf.set(numpy.sin(
            numpy.linspace(0, 2*numpy.pi*sin_ph.get(), sin_len.get())))
    sin_wf = Waveform('SIN', datatype = float, length = 1024)
    # Check we can update its value before iocInit as per #22
    sin_wf.set([1, 2, 3])
    sin_len = longOut(
        'SINN', 0, 1024, initial_value=1024, on_update=update_sin_wf)
    sin_ph = aOut('SINP', initial_value = 0.0, on_update = update_sin_wf)


    wf_len = 32
    wf = numpy.sin(numpy.linspace(0, 2*numpy.pi, wf_len))
    Waveform('WAVEFORM', wf)
    WaveformOut('WAVEFORM_OUT', wf, on_update = on_update)
    Waveform('WAVEFORM2', length = 10)

    longStringOut('LONGSTRING', length = 256)
    longStringIn(
        'AVERYLONGRECORDSUFFIXTOMAKELONGPV',
        initial_value="A long string that is more than 40 characters long"
    )

create_records()

softioc.devIocStats(ioc_name)

__all__ = ['t_ai', 't_ao', ]

if __name__ == "__main__":
    WriteRecords("expected_records.db")
