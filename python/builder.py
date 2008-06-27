'''Support for using the builder in cooperation with the python soft ioc.'''

import os
import device
import numpy
from softioc import dbLoadDatabase

import dls.builder
dls.builder.Configure(
    recordnames = dls.builder.DiamondRecordNames(version = '3.14'),
    iocwriter = dls.builder.SimpleIocWriter())


from dls.builder import *

ModuleVersion('PythonDevice',
    home = os.path.join(os.path.dirname(__file__), '..'),
    use_name = False)


# ----------------------------------------------------------------------------
#  PythonDevice core definitions


class RecordWrapper(object):
    '''This class wraps both a builder and a Python device record instance.
    From the outside it looks like a builder record until the database is
    written.'''

    __Instances = []
    __builder_reset = False

    def __init__(self, builder, device, name, address, **fields):
        assert not self.__builder_reset, \
            'It\'s too late to create records'
        # List of keyword arguments expected by the device constructor.  The
        # remaining arguments are passed to the builder.
        DeviceKeywords = ['on_update', 'validate', 'initial_value', 'out']
        device_kargs = {}
        for keyword in DeviceKeywords:
            if keyword in fields:
                device_kargs[keyword] = fields.pop(keyword)
        
        self.__set('__builder', builder(name, **fields))
        self.__set('__device',  device(address, **device_kargs))
        self.__Instances.append(self)

    def __set(self, field, value):
        if field[:2] == '__' and field[-2:] != '__':
            field = '_' + self.__class__.__name__ + field
        self.__dict__[field] = value

    @classmethod
    def reset_builder(cls):
        cls.__builder_reset = True
        for instance in cls.__Instances:
            instance.__set('__builder', None)

            
    # Most attributes delegate directly to the builder instance until the
    # database has been written.  At this point the builder instance has been
    # deleted, and an attribute error will be raised instead.
            
    def __getattr__(self, field):
        try:
            return getattr(self.__device, field)
        except AttributeError:
            if self.__builder is None:
                raise 
            else:
                return getattr(self.__builder, field)

    def __setattr__(self, field, value):
        if self.__builder is None:
            raise AttributeError('builder has been written')
        else:
            return setattr(self.__builder, field, value)

    # Some further "Duck typing" for the builder: the following are required
    # for links to work properly.
    
    def __call__(self, *specifiers):
        return self.__builder(*specifiers)

    def __str__(self):
        return str(self.__builder)
        


class PythonDevice(Device):
    DbdFileList = ['device.dbd']

    @classmethod
    def __init_class__(cls):
        for name, link in [
                ('ai',        'INP'), ('ao',        'OUT'),
                ('bi',        'INP'), ('bo',        'OUT'),
                ('longin',    'INP'), ('longout',   'OUT'),
                ('mbbi',      'INP'), ('mbbo',      'OUT'),
                ('stringin',  'INP'), ('stringout', 'OUT'),
                ('waveform',  'INP')]:
            setattr(cls, name, cls.makeRecord(name, link))

    class makeRecord:
        def __init__(self, name, link):
            self.builder = getattr(records, name)
            self.device  = getattr(device, name)
            self.link = link

        def __call__(self, name, **fields):
            address = _AddressPrefix + fields.pop('address', name)
            record = RecordWrapper(
                self.builder, self.device, name, address,
                DTYP = 'Python', **fields)
            setattr(record, self.link, '@' + address)
            return record

PythonDevice.__init_class__()
PythonDevice()

_AddressPrefix = ''
def SetAddressPrefix(prefix):
    '''This routine sets a prefix which is added to each record name.'''
    global _AddressPrefix
    _AddressPrefix = prefix


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
    return _in_record('ai', name, 
        LOPR = LOPR,    HOPR = HOPR,
        EGUL = LOPR,    EGUF = HOPR, **fields)

def aOut(name, LOPR=None, HOPR=None, **fields):
    return PythonDevice.ao(name,
        LOPR = LOPR,    HOPR = HOPR,
        EGUL = LOPR,    EGUF = HOPR, **fields)

    
def boolIn(name, ZNAM=None, ONAM=None, **fields):
    return _in_record('bi', name, ZNAM = ZNAM, ONAM = ONAM, **fields)

def boolOut(name, ZNAM=None, ONAM=None, **fields):
    return PythonDevice.bo(name,
        OMSL = 'supervisory', 
        ZNAM = ZNAM, ONAM = ONAM, **fields)


def longIn(name, LOPR=None, HOPR=None, EGU=None, MDEL=-1, **fields):
    return _in_record('longin', name,
        MDEL = MDEL,  EGU  = EGU,
        LOPR = LOPR,  HOPR = HOPR, **fields)

def longOut(name, DRVL=None, DRVH=None, **fields):
    return PythonDevice.longout(name,
        OMSL = 'supervisory',
        DRVL = DRVL, DRVH = DRVH, **fields)


# Field name prefixes for mbbi/mbbo records.
_mbbPrefixes = [
    'ZR', 'ON', 'TW', 'TH', 'FR', 'FV', 'SX', 'SV',     # 0-7
    'EI', 'NI', 'TE', 'EL', 'TV', 'TT', 'FT', 'FF']     # 8-15

# Adds a list of (option, value [,severity]) tuples into field settings
# suitable for mbbi and mbbo records.
def _process_mbb_values(option_values, fields):
    def process_value(prefix, option, value, severity=None):
        fields[prefix + 'ST'] = option
        fields[prefix + 'VL'] = value
        if severity:
            fields[prefix + 'SV'] = severity
    for default_value, (prefix, value) in \
            enumerate(zip(_mbbPrefixes, option_values)):
        if isinstance(value, str):
            # The value is a simple string naming the option.  Assign a
            # default numerical value (and no severity setting).
            process_value(prefix, value, default_value)
        else:
            # The value is two- or three-tuple consisting of an option name, a
            # corresponding numerical value and an alarm severity.
            process_value(prefix, *value)
        
def mbbIn(name, *option_values, **fields):
    _process_mbb_values(option_values, fields)
    return _in_record('mbbi', name, **fields)

def mbbOut(name, *option_values, **fields):
    _process_mbb_values(option_values, fields)
    return PythonDevice.mbbo(name, OMSL = 'supervisory', **fields)


def stringIn(name, **fields):
    return _in_record('stringin', name, **fields)
    
def stringOut(name, **fields):
    return PythonDevice.stringout(name, **fields)


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
    return _in_record('waveform', name, out = False, **fields)

WaveformIn = Waveform

def WaveformOut(name, *value, **fields):
    _waveform(value, fields)
    return PythonDevice.waveform(name, out = True, **fields)



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

    RecordWrapper.reset_builder()


def SetDeviceName(device_name):
    '''Wrapper for the builder SetDevice functionality.'''
    domain, area, component, id = device_name.split('-')
    SetDomain(domain, area)
    SetDevice(component, int(id, 10))
    


__all__ = [
    # Re-exports from dls.builder
    'records',
    'PP', 'CP', 'MS', 'NP',
    'SetDomain', 'SetDevice', 'GetDevice', 'UnsetDevice',
    # Wrappers for PythonDevice
    'aIn',      'aOut',
    'boolIn',   'boolOut',
    'longIn',   'longOut',
    'stringIn', 'stringOut',
    'mbbIn',    'mbbOut',
    'Waveform',
    # Other builder support functions
    'PythonDevice',
    'LoadDatabase',
    'SetDeviceName',
]
