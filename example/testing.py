# Simple script for build a set of test PVs.

from builder import *
import numpy

SetDeviceName('TS-DI-TEST-01')


def on_update(value):
    print 'on_update', repr(value)


t_ai        = aIn('AI')
t_boolin    = boolIn('BOOLIN', 'True', 'False')
t_longin    = longIn('LONGIN')
t_stringin  = stringIn('STRINGIN')
t_mbbi      = mbbIn('MBBI', 'One', 'Two', 'Three')

for rec in [t_ai, t_boolin, t_longin, t_stringin, t_mbbi]:
    rec.PINI = 'YES'

t_ao        = aOut      ('AO', initial_value = 12.45)
t_boolout   = boolOut   ('BOOLOUT', 'Zero', 'One', initial_value = True)
t_longout   = longOut   ('LONGOUT', initial_value = 2008)
t_stringout = stringOut ('STRINGOUT', initial_value = 'watevah')
t_mbbo      = mbbOut    ('MBBO', 'Ein', 'Zwei', 'Drei',
    initial_value = 1)

for rec in [t_ao, t_boolout, t_longout, t_stringout, t_mbbo]:
    rec.set_on_update(on_update)


t_ai.set(12.34)
t_boolin.set(False)
t_longin.set(33)
t_stringin.set('Testing string')
t_mbbi.set(2)


wf = numpy.sin(numpy.linspace(0, 2*numpy.pi, 32))
t_waveform_in  = Waveform('WAVEFORM', wf)
t_waveform_out = WaveformOut('WAVEFORM_OUT', wf, on_update = on_update)



def Update():
    t_ai.set(3.14159)
    t_boolin.set(True)
    t_longin.set(365)
    t_stringin.set('Another different string')
    t_mbbi.set(0)
    

__all__ = [
    't_ai', 't_boolin',  't_longin',  't_stringin',  't_mbbi',
    't_ao', 't_boolout', 't_longout', 't_stringout', 't_mbbo',
    't_waveform_in', 't_waveform_out',
    'Update'
]
