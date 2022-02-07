import os
import numpy
from .softioc import dbLoadDatabase

from epicsdbbuilder import *

InitialiseDbd()
LoadDbdFile(os.path.join(os.path.dirname(__file__), 'device.dbd'))

from . import device, pythonSoftIoc  # noqa

PythonDevice = pythonSoftIoc.PythonDevice()


# ----------------------------------------------------------------------------
#  Wrappers for PythonDevice record constructors.
#
# The SCAN field for all input records defaults to I/O Intr.


def _in_record(record, name, **fields):
    '''For input records we provide some automatic extra features: scanning,
    initialisation as appropriate, and blocking puts from outside the IOC.'''

    fields.setdefault('SCAN', 'I/O Intr')
    if 'initial_value' in fields:
        fields.setdefault('PINI', 'YES')
    fields.setdefault('DISP', 1)
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

# All the severity strings supported by <prefix>SV
_severityStrings = ['NO_ALARM', 'MINOR', 'MAJOR', 'INVALID']

# Converts a list of (option [,severity]) values or tuples into field settings
# suitable for mbbi and mbbo records.
def _process_mbb_values(options, fields):
    def process_value(prefix, value, option, severity=None):
        fields[prefix + 'ST'] = option
        fields[prefix + 'VL'] = value
        if severity:
            if isinstance(severity, int):
                # Map alarm.MINOR_ALARM -> "MINOR"
                severity = _severityStrings[severity]
            fields[prefix + 'SV'] = severity
    # zip() silently ignores extra values in options, so explicitly check length
    assert len(options) <= 16, 'May not specify more than 16 enum values'
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


# Converts numpy dtype name to FTVL value.
NumpyDtypeToDbf = {
    'int8':     'CHAR',
    'uint8':    'UCHAR',
    'int16':    'SHORT',
    'uint16':   'USHORT',
    'int32':    'LONG',
    'uint32':   'ULONG',
    'float32':  'FLOAT',
    'float64':  'DOUBLE',
}

# Coverts FTVL string to numpy type
DbfStringToNumpy = {
    'CHAR':     'int8',
    'UCHAR':    'uint8',
    'SHORT':    'int16',
    'USHORT':   'uint16',
    'LONG':     'int32',
    'ULONG':    'uint32',
    'FLOAT':    'float32',
    'DOUBLE':   'float64',
}


def _get_length(fields, default = None):
    '''Helper function for getting 'length' or 'NELM' from arguments'''

    if 'length' in fields:
        assert 'NELM' not in fields, 'Cannot specify NELM and length together'
        return fields.pop('length')
    elif 'NELM' in fields:
        return fields.pop('NELM')
    else:
        assert default is not None, 'Must specify waveform length'
        return default


def _waveform(value, fields):
    '''Helper routine for waveform construction.  If a value is given it is
    interpreted as an initial value and used to configure length and datatype
    (unless these are overridden), otherwise length and datatype must be
    specified.'''

    if 'initial_value' in fields:
        assert not value, 'Can\'t specify initial value twice!'
        value = (fields.pop('initial_value'),)

    # Datatype can be specified as keyword argument, taken from FTVL, or derived
    # from the initial value
    if 'datatype' in fields:
        assert 'FTVL' not in fields, \
            'Can\'t specify FTVL and datatype together'
        datatype = fields.pop('datatype')
        if datatype == int or datatype == 'int':
            # Convert Python int to 32-bit integer, it's all we can handle
            datatype = numpy.dtype('int32')
        else:
            datatype = numpy.dtype(datatype)
    elif 'FTVL' in fields:
        datatype = numpy.dtype(DbfStringToNumpy[fields['FTVL']])
    else:
        # No datatype specified, will have to infer from initial value
        datatype = None

    if value:
        # If a value is specified it should be the *only* non keyword argument.
        value, = value
        initial_value = device._require_waveform(value, datatype)
        length = _get_length(fields, len(initial_value))

        # Special case for [u]int64: if the initial value comes in as 64 bit
        # integers we cannot represent that, so recast it as [u]int32
        if datatype is None:
            if initial_value.dtype == numpy.int64:
                initial_value = numpy.require(initial_value, numpy.int32)
            elif initial_value.dtype == numpy.uint64:
                initial_value = numpy.require(initial_value, numpy.uint32)
    else:
        initial_value = numpy.array([], dtype = datatype)
        length = _get_length(fields)
    datatype = initial_value.dtype

    assert length > 0, 'Array cannot be of zero length'

    fields['initial_value'] = initial_value
    fields['_wf_nelm'] = length
    fields['_wf_dtype'] = datatype

    fields['NELM'] = length
    fields['FTVL'] = NumpyDtypeToDbf[datatype.name]


def Waveform(name, *value, **fields):
    _waveform(value, fields)
    return _in_record('waveform', name, **fields)

WaveformIn = Waveform

def WaveformOut(name, *value, **fields):
    _waveform(value, fields)
    return PythonDevice.waveform_out(name, **fields)


def _long_string(fields):
    if 'length' in fields:
        length = fields.pop('length')
    elif 'initial_value' in fields:
        length = len(fields['initial_value'].encode(errors = 'replace')) + 1
    else:
        # Default length of 256
        length = 256

    fields.setdefault('initial_value', '')
    fields['_wf_nelm'] = length
    fields['_wf_dtype'] = numpy.dtype('uint8')

    fields['NELM'] = length
    fields['FTVL'] = 'UCHAR'


def longStringIn(name, **fields):
    _long_string(fields)
    return _in_record('long_stringin', name, **fields)

def longStringOut(name, **fields):
    _long_string(fields)
    return PythonDevice.long_stringout(name, **fields)



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
    'longStringIn', 'longStringOut',
    'Action',
    # Other builder support functions
    'LoadDatabase',
    'SetDeviceName', 'UnsetDevice'
]
