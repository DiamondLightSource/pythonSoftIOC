import os
import time
import ctypes
from ctypes import *
import numpy

from . import alarm
from . import fields
from .imports import (
    create_callback_capsule,
    dbLoadDatabase,
    signal_processing_complete,
    recGblResetAlarms,
    db_put_field,
)
from .device_core import DeviceSupportCore, RecordLookup


# This is set from softioc.iocInit
dispatcher = None

# Global blocking flag, used to mark asynchronous (False) or synchronous (True)
# processing modes for Out records.
# Default False to maintain behaviour from previous versions.
blocking = False

# Set the current global blocking flag, and return the previous value.
def SetBlocking(new_val):
    global blocking
    old_val = blocking
    blocking = new_val
    return old_val


# EPICS processing return codes
EPICS_OK = 0
EPICS_ERROR = 1
NO_CONVERT = 2


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
    _epics_rc_ = EPICS_OK


    # Most subclasses (all except waveforms) define a ctypes constructor for the
    # underlying EPICS compatible value.
    def _value_to_epics(self, value):
        return self._ctype_(value)

    def _epics_to_value(self, epics):
        return epics.value

    def _default_value(self):
        return self._ctype_()

    def _compare_values(self, value1, value2):
        return value1.value == value2.value


    # This method is called during Out record processing to return the
    # underlying value in EPICS format.
    def _read_value(self, record):
        # Take a true copy of the value read to avoid accidental sharing
        result = self._ctype_()
        result.value = record.read_val().value
        return result

    # This method is called during In record processing to update the
    # underlying value (the value must be in EPICS compatible format).  This is
    # also called during Out record initialisation and value reversion when
    # required.
    def _write_value(self, record, value):
        record.write_val(value)


class ProcessDeviceSupportIn(ProcessDeviceSupportCore):
    _link_ = 'INP'

    def __init__(self, name, **kargs):
        if 'initial_value' in kargs:
            value = self._value_to_epics(kargs.pop('initial_value'))
        else:
            value = self._default_value()

        # We implement update locking via a simple trick which relies on the
        # Python global interpreter lock: this ensures that assigning or
        # reading a single value is atomic.  We therefore cluster all our
        # variable state into a single tuple which represents a single value
        # to be processed.
        #    The tuple contains everything needed to be written: the value,
        # severity, alarm and optional timestamp.
        self._value = (value, alarm.NO_ALARM, alarm.UDF_ALARM, None)
        self.__super.__init__(name, **kargs)

    def _process(self, record):
        # For input process we copy the value stored in the instance to the
        # record.  The alarm status is also updated, and a custom timestamp
        # can also be set.
        value, severity, alarm, timestamp = self._value
        self._write_value(record, value)
        self.process_severity(record, severity, alarm)
        if timestamp is not None:
            record.TIME = timestamp
        record.UDF = 0
        return self._epics_rc_

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
        return self._epics_to_value(self._value[0])


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
        self.__enable_write = True

        if 'initial_value' in kargs:
            self._value = self._value_to_epics(kargs.pop('initial_value'))
        else:
            self._value = None

        self._blocking = kargs.pop('blocking', blocking)
        if self._blocking:
            self._callback = create_callback_capsule()

        self.__super.__init__(name, **kargs)

    def init_record(self, record):
        '''Special record initialisation for out records only: implements
        special record initialisation if an initial value has been specified,
        allowing out records to have a sensible initial value.'''
        if self._value is None:
            # Cannot set in __init__ (like we do for In records), as we want
            # the record alarm status to be set if no value was provided
            # Probably related to PythonSoftIOC issue #53
            self._value = self._default_value()
        else:
            self._write_value(record, self._value)
            if 'MLST' in self._fields_:
                record.MLST = self._value
            record.TIME = time.time()
            record.UDF = 0
            recGblResetAlarms(record)
        return self._epics_rc_

    def __completion(self, record):
        '''Signals that all on_update processing is finished'''
        if self._blocking:
            signal_processing_complete(record, self._callback)

    def _process(self, record):
        '''Processing suitable for output records.  Performs immediate value
        validation and asynchronous update notification.'''

        if record.PACT:
            return EPICS_OK

        value = self._read_value(record)
        if not self.__always_update and \
                self._compare_values(value, self._value):
            # If the value isn't making a change then don't do anything.
            return EPICS_OK

        python_value = self._epics_to_value(value)
        if self.__enable_write and self.__validate and \
                not self.__validate(self, python_value):
            # Asynchronous validation rejects value, so restore the last good
            # value.
            self._write_value(record, self._value)
            return EPICS_ERROR
        else:
            # Value is good.  Hang onto it, let users know the value has changed
            self._value = value
            record.UDF = 0
            if self.__on_update and self.__enable_write:
                record.PACT = self._blocking
                dispatcher(
                    self.__on_update,
                    func_args=(python_value,),
                    completion = self.__completion,
                    completion_args=(record,))

            return EPICS_OK


    def _value_to_dbr(self, value):
        return self._dbf_type_, 1, addressof(value), value


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
            # The array parameter is used to keep the raw pointer alive
            dbf_code, length, data, array = self._value_to_dbr(value)
            self.__enable_write = process
            db_put_field(_record.NAME, dbf_code, data, length)
            self.__enable_write = True

    def get(self):
        if self._value is None:
            # Before startup complete if no value set return default value
            value = self._default_value()
        else:
            value = self._value
        return self._epics_to_value(value)


def _Device(Base, record_type, ctype, dbf_type, epics_rc, mlst = False):
    '''Wrapper for generating simple records.'''
    class GenericDevice(Base):
        _record_type_ = record_type
        _device_name_ = 'devPython_' + record_type
        _fields_ = ['UDF', 'VAL']
        _epics_rc_ = epics_rc
        _ctype_ = staticmethod(ctype)
        _dbf_type_ = dbf_type
        if mlst:
            _fields_.append('MLST')

    GenericDevice.__name__ = record_type
    return GenericDevice

_In = ProcessDeviceSupportIn
_Out = ProcessDeviceSupportOut

def _Device_In(*args, **kargs):
    return _Device(_In, mlst = False, *args, **kargs)

def _Device_Out(*args, **kargs):
    return _Device(_Out, mlst = True, *args, **kargs)

longin = _Device_In('longin', c_int32, fields.DBF_LONG, EPICS_OK)
longout = _Device_Out('longout', c_int32, fields.DBF_LONG, EPICS_OK)
bi = _Device_In('bi', c_uint16, fields.DBF_CHAR, NO_CONVERT)
bo = _Device_Out('bo', c_uint16, fields.DBF_CHAR, NO_CONVERT)
mbbi = _Device_In('mbbi', c_uint16, fields.DBF_SHORT, NO_CONVERT)
mbbo = _Device_Out('mbbo', c_uint16, fields.DBF_SHORT, NO_CONVERT)


def _string_at(value, count):
    # Need string_at() twice to ensure string is size limited *and* null
    # terminated.
    value = ctypes.string_at(ctypes.string_at(value, count))
    # Convert bytes to unicode string
    return value.decode(errors = 'replace')

class EpicsString:
    _fields_ = ['UDF', 'VAL']
    _epics_rc_ = EPICS_OK
    _ctype_ = c_char * 40
    _dbf_type_ = fields.DBF_STRING

    def _value_to_epics(self, value):
        # It's a little odd: we can't simply construct a value from the byte
        # string, but we can update the array in an existing value.
        # Value being written must be a string, and will be automatically null
        # terminated where possible.
        result = self._ctype_()
        result.value = value.encode() + b'\0'
        return result

    def _epics_to_value(self, epics):
        return _string_at(epics, 40)


class stringin(EpicsString, ProcessDeviceSupportIn):
    _record_type_ = 'stringin'
    _device_name_ = 'devPython_stringin'

class stringout(EpicsString, ProcessDeviceSupportOut):
    _record_type_ = 'stringout'
    _device_name_ = 'devPython_stringout'


dset_process_linconv = (
    [('process',         CFUNCTYPE(c_int, c_void_p)),
     ('special_linconv', CFUNCTYPE(c_int, c_void_p, c_int))],
    [0, 0])

# For ai and ao there's no point in supporting RVAL <-> VAL conversion, so
# for these we support no conversion directly.

class ai(ProcessDeviceSupportIn):
    _record_type_ = 'ai'
    _device_name_ = 'devPython_ai'
    _fields_ = ['UDF', 'VAL']
    _dset_extra_ = dset_process_linconv
    _epics_rc_ = NO_CONVERT
    _ctype_ = c_double
    _dbf_type_ = fields.DBF_DOUBLE

    def _process(self, record):
        # Because we're returning NO_CONVERT we need to do the .UDF updating
        # ourself (otherwise the record support layer does this).
        record.UDF = int(numpy.isnan(self._value[0]))
        return self.__super._process(record)

class ao(ProcessDeviceSupportOut):
    _record_type_ = 'ao'
    _device_name_ = 'devPython_ao'
    _fields_ = ['UDF', 'VAL', 'MLST']
    _dset_extra_ = dset_process_linconv
    _epics_rc_ = NO_CONVERT
    _ctype_ = c_double
    _dbf_type_ = fields.DBF_DOUBLE


def _require_waveform(value, dtype):
    if isinstance(value, bytes):
        # Special case hack for byte arrays.  Surprisingly tricky:
        value = numpy.frombuffer(value, dtype = numpy.uint8)
    value = numpy.require(value, dtype = dtype)
    if value.shape == ():
        value.shape = (1,)
    assert value.ndim == 1, 'Can\'t write multidimensional arrays'
    return value


class WaveformBase(ProcessDeviceSupportCore):
    _link_ = 'INP'
    # In the waveform record class, the following four fields are key:
    #   FTVL    Type of stored waveform (as a DBF_ code)
    #   BPTR    Pointer to raw array containing waveform data
    #   NELM    Length of allocated array in number of elements
    #   NORD    Currently reported length of array (0 <= NORD <= NELM)
    _fields_ = ['UDF', 'FTVL', 'BPTR', 'NELM', 'NORD']


    def __init__(self, name, _wf_nelm, _wf_dtype, **kargs):
        self._dtype = _wf_dtype
        self._nelm = _wf_nelm
        self.__super.__init__(name, **kargs)

    def init_record(self, record):
        self._dbf_type_ = record.FTVL
        return self.__super.init_record(record)

    def _read_value(self, record):
        nord = record.NORD
        result = numpy.empty(nord, dtype = self._dtype)
        memmove(
            result.ctypes.data_as(c_void_p), record.BPTR,
            self._dtype.itemsize * nord)
        return result

    def _write_value(self, record, value):
        nord = len(value)
        memmove(
            record.BPTR, value.ctypes.data_as(c_void_p),
            self._dtype.itemsize * nord)
        record.NORD = nord

    def _compare_values(self, value, other):
        return numpy.array_equal(value, other)

    def _value_to_epics(self, value):
        # Ensure we always convert incoming value into numpy array, regardless
        # of whether the record has been initialised or not
        value = _require_waveform(value, self._dtype)
        # Because arrays are mutable values it's ever so easy to accidentially
        # call set() with a value which subsequently changes.  To avoid this
        # common class of bug, at the cost of duplicated code and data, here we
        # ensure a copy is taken of the value.
        assert len(value) <= self._nelm, 'Value too long for waveform'
        return +value

    def _epics_to_value(self, value):
        return value

    def _value_to_dbr(self, value):
        return self._dbf_type_, len(value), value.ctypes.data, value


class waveform(WaveformBase, ProcessDeviceSupportIn):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform'

class waveform_out(WaveformBase, ProcessDeviceSupportOut):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform_out'


class LongStringBase(WaveformBase):
    _dtype = numpy.dtype('uint8')

    def _value_to_epics(self, value):
        value = value.encode(errors = 'replace')
        # Convert a string into an array of characters.  This will produce
        # the correct behaviour when treating a character array as a string.
        # Note that the trailing null is needed to work around problems with
        # some clients.
        value = numpy.frombuffer(value + b'\0', dtype = numpy.uint8)
        # Ensure string isn't too long to fit into waveform
        assert len(value) <= self._nelm, 'Value too long for waveform'
        return value

    def _epics_to_value(self, value):
        return _string_at(value.ctypes, len(value))


class long_stringin(LongStringBase, ProcessDeviceSupportIn):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_long_stringin'

class long_stringout(LongStringBase, ProcessDeviceSupportOut):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_long_stringout'


# Ensure the .dbd file is loaded.
dbLoadDatabase('device.dbd', os.path.dirname(__file__), None)
