'''Support for using the builder in cooperation with the python soft ioc.'''

import os
import device
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
                raise AttributeError('builder has been written')
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


def aIn(name, LOPR=None, HOPR=None, **fields):
    fields.setdefault('SCAN', 'I/O Intr')
    return PythonDevice.ai(name,
        LOPR = LOPR,    HOPR = HOPR,
        EGUL = LOPR,    EGUF = HOPR, **fields)

def aOut(name, LOPR=None, HOPR=None, **fields):
    return PythonDevice.ao(name,
        LOPR = LOPR,    HOPR = HOPR,
        EGUL = LOPR,    EGUF = HOPR, **fields)

    
def boolIn(name, ZNAM=None, ONAM=None, **fields):
    fields.setdefault('SCAN', 'I/O Intr')
    return PythonDevice.bi(name, ZNAM = ZNAM, ONAM = ONAM, **fields)

def boolOut(name, ZNAM=None, ONAM=None, **fields):
    return PythonDevice.bo(name,
        OMSL = 'supervisory', 
        ZNAM = ZNAM, ONAM = ONAM, **fields)


def longIn(name, LOPR=None, HOPR=None, EGU=None, MDEL=-1, **fields):
    fields.setdefault('SCAN', 'I/O Intr')
    return PythonDevice.longin(name,
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
def _process_mbb_values(fields, option_values):
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
    fields.setdefault('SCAN', 'I/O Intr')
    _process_mbb_values(fields, option_values)
    return PythonDevice.mbbi(name, **fields)

def mbbOut(name, *option_values, **fields):
    _process_mbb_values(fields, option_values)
    return PythonDevice.mbbo(name, OMSL = 'supervisory', **fields)


def stringIn(name, **fields):
    fields.setdefault('SCAN', 'I/O Intr')
    return PythonDevice.stringin(name, **fields)
    
def stringOut(name, **fields):
    return PythonDevice.stringout(name, **fields)
    

def Waveform(name, length, FTVL='FLOAT', **fields):
    if not fields.get('out', False):
        fields.setdefault('SCAN', 'I/O Intr')
    return PythonDevice.waveform(name,
        NELM = length, FTVL = FTVL, **fields)



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
