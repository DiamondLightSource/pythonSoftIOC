import os
import sys
import time
import numpy

from ctypes import *
from . import alarm
from .fields import DbfCodeToNumpy, DbrToDbfCode
from .imports import dbLoadDatabase, recGblResetAlarms, db_put_field
from .device_core import DeviceSupportCore, RecordLookup


# This is set from softioc.iocInit
# dispatcher(func, *args) will queue a callback to happen
dispatcher = None


# EPICS processing return codes
EPICS_OK = 0
EPICS_ERROR = 1
NO_CONVERT = 2

NumpyCharCodeToDbr = {
        # The following type codes are supported directly:
        'S':    0,  # DBR_STRING     str_
        'h':    1,  # DBR_SHORT      short  = int16
        'f':    2,  # DBR_FLOAT      single = float32
        'b':    4,  # DBR_CHAR       byte   = int8
        'i':    5,  # DBR_LONG       intc   = int32
        'd':    6,  # DBR_DOUBLE     float_ = float64
        # These are supported as related types
        'H':    1,  # DBR_SHORT      ushort = uint16
        '?':    4,  # DBR_CHAR       bool_
        'B':    4,  # DBR_CHAR       ubyte  = uint8
        'I':    5,  # DBR_LONG       uintc  = uint32
    }
if numpy.int_().itemsize == 4:
    NumpyCharCodeToDbr.update({'l': 5, 'L': 5})   # int_, uint


class ProcessDeviceSupportCore(DeviceSupportCore, RecordLookup):
    '''Implements canonical default processing for records with a _process
    method.  Processing typically either copies a locally set value into the
    record, or else reads a value from the record and triggers an update.
    '''

    # Most records just have an extra process method, but unfortunately ai/ao
    # will have to override this to also add their special_linconv method.
    _dset_extra_ = ([('process', CFUNCTYPE(c_int, c_void_p))], [0])

    # For some record types we want to return a different return code either
    # from record init or processing
    _epics_rc = EPICS_OK

    # Function to convert an incoming Python value into EPICS-appropriate form.
    def _value_to_epics(self, value):
        return value

    # Default implementations of read and write, overwritten where necessary.
    def _read_value(self, record):
        return getattr(record, 'VAL')
    def _write_value(self, record, value):
        setattr(record, 'VAL', value)

    # Converts a Python value into a form suitable for sending over channel
    # access.  Derived from the corresponding cothread implementation.  Returns
    # computed dbrcode, waveform length, raw data pointer and pointer to
    # underlying data (for lifetime management).
    def value_to_dbr(self, value):

        if isinstance(value, str):
            value = value.encode(errors='replace')

        # First convert the data directly into an array.  This will help in
        # subsequent processing: this does most of the type coercion.
        value = numpy.require(value, requirements = 'C')
        if value.shape == ():
            value.shape = (1,)
        assert value.ndim == 1, 'Can\'t put multidimensional arrays!'

        if value.dtype.char == 'S':
            # Need special processing to hack the array so that strings are
            # actually 40 characters long.
            new_value = numpy.empty(value.shape, 'S40')
            new_value[:] = value
            value = new_value

        try:
            dbrtype = NumpyCharCodeToDbr[value.dtype.char]
        except KeyError:
            # One more special case.  caput() of a list of integers on a 64-bit
            # system will fail at this point because they were automatically
            # converted to 64-bit integers.  Catch this special case and fix it
            # up by silently converting to 32-bit integers.  Not really the
            # right thing to do (as data can be quietly lost), but the
            # alternative isn't nice to use either.
            if value.dtype.char == 'l':
                value = numpy.require(value, dtype = numpy.int32)
                dbrtype = 5
            else:
                raise

        return dbrtype, len(value), value.ctypes.data, value

class ProcessDeviceSupportIn(ProcessDeviceSupportCore):
    _link_ = 'INP'

    def __init__(self, name, **kargs):
        # We implement update locking via a simple trick which relies on the
        # Python global interpreter lock: this ensures that assigning or
        # reading a single value is atomic.  We therefore cluster all our
        # variable state into a single tuple which represents a single value
        # to be processed.

        value = self._value_to_epics(
            kargs.pop('initial_value', self._default_))

        #    The tuple contains everything needed to be written: the value,
        # severity, alarm and optional timestamp.
        self._value = (value, alarm.NO_ALARM, alarm.UDF_ALARM, None)
        self.__super.__init__(name, **kargs)

    def _process(self, record, _value=None):
        # For input process we copy the value stored in the instance to the
        # record.  The alarm status is also updated, and a custom timestamp
        # can also be set.
        if _value is None:
            _value = self._value
        value, severity, alarm, timestamp = _value
        self._write_value(record, value)
        self.process_severity(record, severity, alarm)
        if timestamp is not None:
            record.TIME = timestamp
        return self._epics_rc

    def set(self, value,
            severity=alarm.NO_ALARM, alarm=alarm.UDF_ALARM, timestamp=None):
        '''Updates the stored value and triggers an update.  The alarm
        severity and timestamp can also be specified if appropriate.'''
        value = self._value_to_epics(value)
        self._value = (value, severity, alarm, timestamp)
        self.trigger()

    def set_alarm(self, severity, alarm, timestamp=None):
        '''Updates the alarm status without changing the stored value.  An
        update is triggered, and a timestamp can optionally be specified.'''
        self._value = (self._value[0], severity, alarm, timestamp)
        self.trigger()

    def get(self):
        '''Returns the last written value.'''
        return self._value[0]


class ProcessDeviceSupportOut(ProcessDeviceSupportCore):
    _link_ = 'OUT'

    def __init__(self, name, **kargs):
        on_update = kargs.pop('on_update', None)
        on_update_name = kargs.pop('on_update_name', None)
        # At most one of on_update and on_update_name can be specified
        assert on_update is None or on_update_name is None, \
            'Cannot specify on_update and on_update_name together'
        if on_update:
            self.__on_update = on_update
        elif on_update_name:
            self.__on_update = lambda value: on_update_name(value, name)
        else:
            self.__on_update = None

        self.__validate = kargs.pop('validate', None)
        self.__always_update = kargs.pop('always_update', False)
        self._value = self._value_to_epics(kargs.pop('initial_value', None))
        self.__enable_write = True
        self.__super.__init__(name, **kargs)

    def init_record(self, record):
        '''Special record initialisation for out records only: implements
        special record initialisation if an initial value has been specified,
        allowing out records to have a sensible initial value.'''
        if self._value is None:
            # Cannot set in __init__, as we want the record alarm status to be
            # set if no value was provided
            self._value = self._default_
        else:
            self._write_value(record, self._value)
            if 'MLST' in self._fields_:
                record.MLST = self._value
            record.TIME = time.time()
            record.UDF = 0
            recGblResetAlarms(record)
        return self._epics_rc

    def _process(self, record):
        '''Processing suitable for output records.  Performs immediate value
        validation and asynchronous update notification.'''
        value = self._read_value(record)
        if numpy.all(value == self._value) and not self.__always_update:
            # If the value isn't making a change then don't do anything.
            return EPICS_OK
        if self.__enable_write and self.__validate and \
                not self.__validate(self, value):
            # Asynchronous validation rejects value.  It's up to the
            # validation routine to do any logging.  In this case restore the
            # last good value.
            if self._value is not None:
                self._write_value(record, self._value)
            return EPICS_ERROR

        self._value = value
        if self.__on_update and self.__enable_write:
            dispatcher(self.__on_update, value)
        return EPICS_OK

    def set(self, value, process=True):
        '''Special routine to set the value directly.'''
        value = self._value_to_epics(value)
        try:
            _record = self._record
        except AttributeError:
            # Record not initialised yet.  Record the value for when
            # initialisation occurs
            self._value = value
        else:
            datatype, length, data, array = self.value_to_dbr(value)
            self.__enable_write = process
            db_put_field(
                _record.NAME, DbrToDbfCode[datatype], data, length)
            self.__enable_write = True

    def get(self):
        return self._value


def _Device(
        Base,
        record_type,
        mlst=False,
        default=0,
        convert=True,
        value_to_epics=None):
    '''Wrapper for generating simple records.'''
    class GenericDevice(Base):
        _record_type_ = record_type
        _device_name_ = 'devPython_' + record_type
        _default_ = default
        _fields_ = ['UDF', 'VAL']
        _epics_rc = EPICS_OK if convert else NO_CONVERT
        if value_to_epics:
            _value_to_epics = \
                staticmethod(value_to_epics)
        if mlst:
            _fields_.append('MLST')

    GenericDevice.__name__ = record_type
    return GenericDevice

_In = ProcessDeviceSupportIn
_Out = ProcessDeviceSupportOut

def _Device_In(record_type, **kargs):
    return _Device(_In,  record_type, **kargs)

def _Device_Out(record_type, convert=True, mlst=True, **kargs):
    return _Device(_Out, record_type, convert=convert, mlst=mlst, **kargs)


def convert_to_int(value):
    """Attempt to convert any type into its integer representation"""
    if type(value) == c_int:
        return value.value
    return int(value) if value else None

def convert_to_float(value):
    """Attempt to convert any type into its float representation"""
    if type(value) == c_float:
        return value.value
    return float(value) if value else None

def truncate_string(value):
    """Trim a string to EPICS 40 (39 with null byte) character limit"""
    if sys.version_info >= (3,):
        if isinstance(value, bytes):
            value = value.decode(errors="replace")
        return value[:39] if isinstance(value, str) else None
    else:
        if isinstance(value, bytes):  # bytes == str in Python2
            value = value.decode("utf-8", errors="replace")
        return value[:39] if isinstance(value, unicode) else None

longin = _Device_In('longin', value_to_epics=convert_to_int)
longout = _Device_Out('longout', value_to_epics=convert_to_int)
bi = _Device_In('bi', convert=False)
bo = _Device_Out('bo', convert=False)
stringin = _Device_In('stringin', mlst=False, default='',
                      value_to_epics=truncate_string)
stringout = _Device_Out('stringout', mlst=False, default='',
                        value_to_epics=truncate_string)
mbbi = _Device_In('mbbi', convert=False)
mbbo = _Device_Out('mbbo', convert=False)


dset_process_linconv = (
    [('process',         CFUNCTYPE(c_int, c_void_p)),
     ('special_linconv', CFUNCTYPE(c_int, c_void_p, c_int))],
    [0, 0])

# For ai and ao there's no point in supporting RVAL <-> VAL conversion, so
# for these we support no conversion directly.

class ai(ProcessDeviceSupportIn):
    _record_type_ = 'ai'
    _device_name_ = 'devPython_ai'
    _default_ = 0.0
    _fields_ = ['UDF', 'VAL']
    _dset_extra_ = dset_process_linconv
    _epics_rc = NO_CONVERT
    _value_to_epics = staticmethod(convert_to_float)

    def _process(self, record):
        _value = self._value
        self.__super._process(record, _value)
        # Because we're returning NO_CONVERT we need to do the .UDF updating
        # ourself (otherwise the record support layer does this).
        record.UDF = int(numpy.isnan(_value[0]))
        return NO_CONVERT

class ao(ProcessDeviceSupportOut):
    _record_type_ = 'ao'
    _device_name_ = 'devPython_ao'
    _default_ = 0.0
    _fields_ = ['UDF', 'VAL', 'MLST']
    _dset_extra_ = dset_process_linconv
    _epics_rc = NO_CONVERT
    _value_to_epics = staticmethod(convert_to_float)



class WaveformBase(ProcessDeviceSupportCore):
    _link_ = 'INP'
    # In the waveform record class, the following four fields are key:
    #   FTVL    Type of stored waveform (as a DBF_ code)
    #   BPTR    Pointer to raw array containing waveform data
    #   NELM    Length of allocated array in number of elements
    #   NORD    Currently reported length of array (0 <= NORD <= NELM)
    _fields_ = ['UDF', 'FTVL', 'BPTR', 'NELM', 'NORD']
    # Allow set() to be called before init_record:
    dtype = None

    _default_ = ()

    def init_record(self, record):
        self.dtype = DbfCodeToNumpy[record.FTVL]
        return self.__super.init_record(record)

    def _read_value(self, record):
        nord = record.NORD
        result = numpy.empty(nord, dtype = self.dtype)
        memmove(
            result.ctypes.data_as(c_void_p), record.BPTR,
            self.dtype.itemsize * nord)
        return result

    def _write_value(self, record, value):
        value = numpy.require(value, dtype = self.dtype)
        if value.shape == ():
            value.shape = (1,)
        assert value.ndim == 1, 'Can\'t write multidimensional arrays'

        nelm = record.NELM
        nord = len(value)
        if nord > nelm:
            nord = nelm
        memmove(
            record.BPTR, value.ctypes.data_as(c_void_p),
            self.dtype.itemsize * nord)
        record.NORD = nord

    def _handle_strings(self, value):
        """Handles strings and bytearrays as values for Waveforms. Returns the
        string converted to a numpy array."""

        if isinstance(value, str):
            value = value.encode(errors="replace")

        if isinstance(value, bytes):
            # Convert a string into an array of characters.  This will produce
            # the correct behaviour when treating a character array as a string.
            # Note that the trailing null is needed to work around problems with
            # some clients. Note this also exists in builder.py's _waveform().
            value = numpy.frombuffer(
                value + b'\0',
                dtype = numpy.uint8
            )

        return value

    def _value_to_epics(self, value):

        # Caused by no initial_value being specified
        if value is None:
            return value

        value = self._handle_strings(value)

        # Ensure we always convert incoming value into numpy array, regardless
        # of whether the record has been initialised or not
        datatype, length, data, array = self.value_to_dbr(value)

        return array


class waveform(WaveformBase, ProcessDeviceSupportIn):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform'

class waveform_out(WaveformBase, ProcessDeviceSupportOut):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform_out'

# Ensure the .dbd file is loaded.
dbLoadDatabase("device.dbd", os.path.dirname(__file__), None)
