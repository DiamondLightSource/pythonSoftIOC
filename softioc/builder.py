import os
import numpy
from .softioc import dbLoadDatabase

from epicsdbbuilder import *

InitialiseDbd()
LoadDbdFile(os.path.join(os.path.dirname(__file__), 'device.dbd'))

from . import pythonSoftIoc  # noqa
PythonDevice = pythonSoftIoc.PythonDevice()



# ----------------------------------------------------------------------------
#  Wrappers for PythonDevice record constructors.
#
# The SCAN field for all input records defaults to I/O Intr.


def _in_record(record, name, **fields):
    '''For input records we provide some automatic extra features: scanning
    and initialisation as appropriate.'''

    fields.setdefault('SCAN', 'I/O Intr')
    if 'initial_value' in fields:
        fields.setdefault('PINI', 'YES')
    return getattr(PythonDevice, record)(name, **fields)


def aIn(name, LOPR=None, HOPR=None, **fields):
    return _in_record(
        'ai', name, LOPR = LOPR, HOPR = HOPR, **fields)

def aOut(name, LOPR=None, HOPR=None, **fields):
    fields.setdefault('DRVL', LOPR)
    fields.setdefault('DRVH', HOPR)
    return PythonDevice.ao(
        name, LOPR = LOPR, HOPR = HOPR, **fields)


def boolIn(name, ZNAM=None, ONAM=None, **fields):
    return _in_record('bi', name, ZNAM = ZNAM, ONAM = ONAM, **fields)

def boolOut(name, ZNAM=None, ONAM=None, **fields):
    return PythonDevice.bo(
        name, OMSL = 'supervisory', ZNAM = ZNAM, ONAM = ONAM, **fields)


def longIn(name, LOPR=None, HOPR=None, EGU=None, **fields):
    fields.setdefault('MDEL', -1)
    return _in_record(
        'longin', name, EGU = EGU, LOPR = LOPR, HOPR = HOPR, **fields)

def longOut(name, DRVL=None, DRVH=None, EGU=None, **fields):
    return PythonDevice.longout(
        name, OMSL = 'supervisory', DRVL = DRVL, DRVH = DRVH, EGU = EGU,
        **fields)


# Field name prefixes for mbbi/mbbo records.
_mbbPrefixes = [
    'ZR', 'ON', 'TW', 'TH', 'FR', 'FV', 'SX', 'SV',     # 0-7
    'EI', 'NI', 'TE', 'EL', 'TV', 'TT', 'FT', 'FF']     # 8-15

# Converts a list of (option [,severity]) values or tuples into field settings
# suitable for mbbi and mbbo records.
def _process_mbb_values(options, fields):
    def process_value(prefix, value, option, severity=None):
        fields[prefix + 'ST'] = option
        fields[prefix + 'VL'] = value
        if severity:
            fields[prefix + 'SV'] = severity
    for prefix, (value, option) in zip(_mbbPrefixes, enumerate(options)):
        if isinstance(option, tuple):
            # The option is tuple consisting of the option name and an optional
            # alarm severity.
            process_value(prefix, value, *option)
        else:
            # The option is a simple string naming the option.  Assign the
            # default numerical value (and no severity setting).
            process_value(prefix, value, option)

def mbbIn(name, *options, **fields):
    _process_mbb_values(options, fields)
    return _in_record('mbbi', name, **fields)

def mbbOut(name, *options, **fields):
    _process_mbb_values(options, fields)
    return PythonDevice.mbbo(name, OMSL = 'supervisory', **fields)


def stringIn(name, **fields):
    return _in_record('stringin', name, **fields)

def stringOut(name, **fields):
    return PythonDevice.stringout(name, **fields)

def Action(name, **fields):
    return boolOut(name, always_update = True, **fields)


# Converts numpy character code to FTVL value.
NumpyCharCodeToFtvl = {
    # The following type codes are supported directly:
    'B':    'UCHAR',        # ubyte
    'b':    'CHAR',         # byte
    'H':    'USHORT',       # ushort
    'h':    'SHORT',        # short
    'i':    'LONG',         # intc
    'L':    'ULONG',        # uint
    'l':    'LONG',         # int_
    'f':    'FLOAT',        # single
    'd':    'DOUBLE',       # float_
    'S':    'STRING',       # str_

    # The following type codes are weakly supported by pretending that
    # they're related types.
    '?':    'CHAR',         # bool_
    'p':    'LONG',         # intp
    'I':    'ULONG',        # uintc
    'P':    'ULONG',        # uintp

    # The following type codes are not supported at all:
    #   q   longlong        Q   ulonglong       g   longfloat
    #   F   csingle         D   complex_        G   clongfloat
    #   O   object_         U   unicode_        V   void
}


def _waveform(value, fields):
    '''Helper routine for waveform construction.  If a value is given it is
    interpreted as an initial value and used to configure length and datatype
    (unless these are overridden), otherwise length and datatype must be
    specified.'''

    if 'initial_value' in fields:
        assert not value, 'Can\'t specify initial value twice!'
        value = (fields.pop('initial_value'),)

    if value:
        # If a value is specified it should be the *only* non keyword
        # argument.
        value, = value
        value = numpy.array(value)
        fields['initial_value'] = value

        # Pick up default length and datatype from initial value
        length = len(value)
        FTVL = NumpyCharCodeToFtvl[value.dtype.char]
    else:
        # No value specified, so require length and datatype to be specified.
        length = fields.pop('length')
        FTVL = 'FLOAT'

    datatype = fields.pop('datatype', None)
    if datatype is not None:
        assert 'FTVL' not in fields, \
            'Can\'t specify FTVL and datatype together'
        FTVL = NumpyCharCodeToFtvl[numpy.dtype(datatype).char]

    fields['NELM'] = length
    fields.setdefault('FTVL', FTVL)


def Waveform(name, *value, **fields):
    _waveform(value, fields)
    return _in_record('waveform', name, **fields)

WaveformIn = Waveform

def WaveformOut(name, *value, **fields):
    _waveform(value, fields)
    return PythonDevice.waveform_out(name, **fields)



# ----------------------------------------------------------------------------
#  Support routines for builder


_DatabaseWritten = False

def LoadDatabase():
    '''This should be called after all the builder records have been created,
    but before calling iocInit().  The database is loaded into EPICS memory,
    ready for operation.'''
    from tempfile import mkstemp
    fd, database = mkstemp('.db')
    os.close(fd)
    WriteRecords(database)
    dbLoadDatabase(database)
    os.unlink(database)

    pythonSoftIoc.RecordWrapper.reset_builder()


# ----------------------------------------------------------------------------
# Record name configuration.  A device name prefix must be specified.

SetSimpleRecordNames(None, ':')

SetDeviceName = SetPrefix
def SetDeviceName(name):
    SetPrefix(name)

def UnsetDevice():
    SetPrefix(None)


__all__ = [
    # Re-exports from epicsdbbuilder
    'records',
    'PP', 'CP', 'MS', 'NP',
    # Wrappers for PythonDevice
    'aIn',      'aOut',
    'boolIn',   'boolOut',
    'longIn',   'longOut',
    'stringIn', 'stringOut',
    'mbbIn',    'mbbOut',
    'Waveform', 'WaveformOut',
    'Action',
    # Other builder support functions
    'LoadDatabase',
    'SetDeviceName', 'UnsetDevice'
]
