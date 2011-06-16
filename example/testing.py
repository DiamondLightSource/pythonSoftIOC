# Simple script for build a set of test PVs.

from softioc.builder import *
import numpy

SetDeviceName('TS-DI-TEST-01')


def on_update(value):
    print 'on_update', repr(value)


t_ai        = aIn('AI')
t_boolin    = boolIn('BOOLIN', 'True', 'False')
t_longin    = longIn('LONGIN')
t_stringin  = stringIn('STRINGIN')
t_mbbi      = mbbIn('MBBI', 'One', 'Two', 'Three')

t_ao        = aOut      ('AO',
    initial_value = 12.45, on_update = on_update)
t_boolout   = boolOut   ('BOOLOUT', 'Zero', 'One',
    initial_value = True, on_update = on_update)
t_longout   = longOut   ('LONGOUT',
    initial_value = 2008, on_update = on_update)
t_stringout = stringOut ('STRINGOUT',
    initial_value = 'watevah', on_update = on_update)
t_mbbo      = mbbOut    ('MBBO', 'Ein', 'Zwei', 'Drei',
    initial_value = 1, on_update = on_update)

def update_sin_wf(value):
    print 'update_sin_wf', value
    sin_wf.set(numpy.sin(
        numpy.linspace(0, 2*numpy.pi*sin_ph.get(), sin_len.get())))
sin_wf = Waveform('SIN', datatype = float, length = 1024)
sin_len = longOut('SINN', 0, 1024,
    initial_value = 1024, on_update = update_sin_wf)
sin_ph = aOut('SINP', initial_value = 0.0, on_update = update_sin_wf)

t_ai.set(12.34)
t_boolin.set(False)
t_longin.set(33)
t_stringin.set('Testing string')
t_mbbi.set(2)


wf_len = 32
wf = numpy.sin(numpy.linspace(0, 2*numpy.pi, wf_len))
t_waveform_in  = Waveform('WAVEFORM', wf)
t_waveform_out = WaveformOut('WAVEFORM_OUT', wf, on_update = on_update)
t_waveform_in2 = Waveform('WAVEFORM2', length = 10)


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


__all__ = [
    't_ai', 't_boolin',  't_longin',  't_stringin',  't_mbbi',
    't_ao', 't_boolout', 't_longout', 't_stringout', 't_mbbo',
    't_waveform_in', 't_waveform_in2', 't_waveform_out', 'wf_len',
    'Update', 'UpdateOut'
]
