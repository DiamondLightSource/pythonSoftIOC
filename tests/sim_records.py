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

t_ai = aIn('AI', initial_value=12.34)
t_boolin = boolIn('BOOLIN', 'True', 'False', initial_value=False)
t_longin = longIn('LONGIN', initial_value=33)
t_stringin = stringIn('STRINGIN', initial_value="Testing string")
t_mbbi = mbbIn(
    'MBBI', ('One', alarm.MAJOR_ALARM), 'Two', ('Three', "MINOR"),
    initial_value=2)

t_ao = aOut('AO', initial_value=12.45, on_update_name=on_update_name)
t_boolout = boolOut(
    'BOOLOUT', 'Zero', 'One', initial_value=True, on_update=on_update)
t_longout = longOut('LONGOUT', initial_value=2008, on_update=on_update)
t_stringout = stringOut(
    'STRINGOUT', initial_value='watevah', on_update=on_update)
t_mbbo = mbbOut(
    'MBBO', 'Ein', 'Zwei', 'Drei', initial_value=1)

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
t_waveform_in = Waveform('WAVEFORM', wf)
t_waveform_out = WaveformOut('WAVEFORM_OUT', wf, on_update = on_update)
t_waveform_in2 = Waveform('WAVEFORM2', length = 10)

t_longstring_in = Waveform('LONGSTRING', length = 256, datatype = numpy.uint8)


def Update():
    t_ai.set(3.14159)
    t_boolin.set(True)
    t_longin.set(365)
    t_stringin.set('Another different string')
    t_mbbi.set(0)

def UpdateOut():
    t_ao.set(3.14159)
    t_boolout.set(True)
    t_longout.set(365)
    t_stringout.set('Another different string')
    t_mbbo.set(2)

softioc.devIocStats(ioc_name)

__all__ = [
    't_ai', 't_boolin',  't_longin',  't_stringin',  't_mbbi',
    't_ao', 't_boolout', 't_longout', 't_stringout', 't_mbbo',
    't_waveform_in', 't_waveform_in2', 't_waveform_out', 't_longstring_in',
    'wf_len',
    'Update', 'UpdateOut'
]

if __name__ == "__main__":
    WriteRecords("expected_records.db")
