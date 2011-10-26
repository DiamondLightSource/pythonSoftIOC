import os
import time
import traceback
from ctypes import *
import numpy

import cothread
from cothread.dbr import value_to_dbr

import alarm
from fields import DbfCodeToNumpy, DbrToDbfCode
from imports import dbLoadDatabase, recGblResetAlarms
from device_core import DeviceSupportCore, RecordLookup

import imports


class ProcessDeviceSupportCore(DeviceSupportCore, RecordLookup):
    '''Implements canonical default processing for records with a _process
    method.  Processing typically either copies a locally set value into the
    record, or else reads a value from the record and triggers an update.
    '''

    # Most records just have an extra process method, but unfortunately ai/ao
    # will have to override this to also add their special_linconv method.
    _dset_extra_ = ([('process', CFUNCTYPE(c_int, c_void_p))], [0])

    # Default implementations of read and write, overwritten where necessary.
    def _read_value(self, record):
        return getattr(record, self._val_field_)
    def _write_value(self, record, value):
        setattr(record, self._val_field_, value)


class ProcessDeviceSupportIn(ProcessDeviceSupportCore):
    _link_ = 'INP'

    def __init__(self, name, **kargs):
        # We implement update locking via a simple trick which relies on the
        # Python global interpreter lock: this ensures that assigning or
        # reading a single value is atomic.  We therefore cluster all our
        # variable state into a single tuple which represents a single value
        # to be processed.
        #    The tuple contains everything needed to be written: the value,
        # severity, alarm and optional timestamp.
        self._value = (
            kargs.pop('initial_value', self._default_),
            alarm.NO_ALARM, alarm.UDF_ALARM, None)
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
        return 0

    def set(self, value,
            severity=alarm.NO_ALARM, alarm=alarm.UDF_ALARM, timestamp=None):
        '''Updates the stored value and triggers an update.  The alarm
        severity and timestamp can also be specified if appropriate.'''
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

    # This queue is used to communicate process update events to a receiving
    # cothread.  A single dispatching process is spawned to consume updates
    # and convert them into synchronous method calls.
    _DeviceCallbackQueue = cothread.ThreadedEventQueue()
    @classmethod
    def DeviceCallbackDispatcher(cls):
        while True:
            try:
                callback, value = cls._DeviceCallbackQueue.Wait()
                callback(value)
            except:
                # As ever: if an exception occurs within a dispatcher we have
                # to report it and carry on.
                print 'Device callback raised exception'
                traceback.print_exc()

    def __init__(self, name, **kargs):
        self.__on_update = kargs.pop('on_update', None)
        self.__validate  = kargs.pop('validate', None)
        self.__always_update = kargs.pop('always_update', False)
        self._value = kargs.pop('initial_value', None)
        self.__super.__init__(name, **kargs)

    def init_record(self, record):
        '''Special record initialisation for out records only: implements
        special record initialisation if an initial value has been specified,
        allowing out records to have a sensible initial value.'''
        if self._value is not None:
            self._write_value(record, self._value)
            if 'MLST' in self._fields_:
                record.MLST = self._value
            record.TIME = time.time()
            record.UDF = 0
            recGblResetAlarms(record)
        return self.__super.init_record(record)

    def _process(self, record):
        '''Processing suitable for output records.  Performs immediate value
        validation and asynchronous update notification.'''
        value = self._read_value(record)
        if numpy.all(value == self._value) and not self.__always_update:
            # If the value isn't making a change then don't do anything.
            return 0
        if self.__validate and not self.__validate(value):
            # Asynchronous validation rejects value.  It's up to the
            # validation routine to do any logging.  In this case restore the
            # last good value.
            if self._value is not None:
                self._write_value(record, self._value)
            return 1

        self._value = value
        if self.__on_update:
            self._DeviceCallbackQueue.Signal((self.__on_update, value))
        return 0

    def set(self, value):
        '''Special routine to set the value directly.'''
        try:
            _record = self._record
        except AttributeError:
            # Record not initialised yet.  Record the value for when
            # initialisation occurs
            self._value = value
        else:
            datatype, length, data, array = value_to_dbr(value, None)
            imports.db_put_field(
                _record.NAME, DbrToDbfCode[datatype], data, length)

    def get(self):
        return self._value


cothread.Spawn(ProcessDeviceSupportOut.DeviceCallbackDispatcher)



def _Device(Base, record_type, rval=False, mlst=False, default=0):
    '''Wrapper for generating simple records.'''
    val_field = rval and 'RVAL' or 'VAL'
    class GenericDevice(Base):
        _record_type_ = record_type
        _device_name_ = 'devPython_' + record_type
        _val_field_   = val_field
        _default_     = default
        _fields_      = ['UDF', val_field]
        if mlst: _fields_.append('MLST')

    GenericDevice.__name__ = record_type
    return GenericDevice

_In  = ProcessDeviceSupportIn
_Out = ProcessDeviceSupportOut
def _Device_In (type, **kargs):
    return _Device(_In,  type, **kargs)
def _Device_Out(type, rval=False, mlst=True):
    return _Device(_Out, type, rval=rval, mlst=mlst, default=None)

longin      = _Device_In ('longin')
longout     = _Device_Out('longout')
bi          = _Device_In ('bi', rval=True)
bo          = _Device_Out('bo', rval=True)
stringin    = _Device_In ('stringin', mlst=False, default='')
stringout   = _Device_Out('stringout', mlst=False)
mbbi        = _Device_In ('mbbi', rval=True)
mbbo        = _Device_Out('mbbo', rval=True)


NO_CONVERT = 2

dset_process_linconv = (
    [('process',         CFUNCTYPE(c_int, c_void_p)),
     ('special_linconv', CFUNCTYPE(c_int, c_void_p, c_int))],
    [0, 0])

# For ai and ao there's no point in supporting RVAL <-> VAL conversion, so
# for these we support no conversion directly.

class ai(ProcessDeviceSupportIn):
    _record_type_ = 'ai'
    _device_name_ = 'devPython_ai'
    _val_field_   = 'VAL'
    _default_     = 0.0
    _fields_      = ['UDF', 'VAL']
    _dset_extra_  = dset_process_linconv

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
    _val_field_   = 'VAL'
    _fields_      = ['UDF', 'VAL', 'MLST']
    _dset_extra_  = dset_process_linconv

    def init_record(self, record):
        self.__super.init_record(record)
        return NO_CONVERT



class WaveformBase(ProcessDeviceSupportCore):
    _link_ = 'INP'
    # In the waveform record class, the following four fields are key:
    #   FTVL    Type of stored waveform (as a DBF_ code)
    #   BPTR    Pointer to raw array containing waveform data
    #   NELM    Length of allocated array in number of elements
    #   NORD    Currently reported length of array (0 <= NORD <= NELM)
    _fields_ = ['UDF', 'FTVL', 'BPTR', 'NELM', 'NORD']

    def init_record(self, record):
        self.dtype = DbfCodeToNumpy[record.FTVL]
        self.itemsize = self.dtype().itemsize
        return self.__super.init_record(record)

    def _read_value(self, record):
        nord = record.NORD
        result = numpy.empty(nord, dtype = self.dtype)
        memmove(result.ctypes.data_as(c_void_p), record.BPTR,
            self.dtype().itemsize * nord)
        return result

    def _write_value(self, record, value):
        value = numpy.require(value, dtype = self.dtype)
        if value.shape == ():  value.shape = (1,)
        assert value.ndim == 1, 'Can\'t write multidimensional arrays'

        nelm = record.NELM
        nord = len(value)
        if nord > nelm:  nord = nelm
        memmove(
            record.BPTR, value.ctypes.data_as(c_void_p), self.itemsize * nord)
        record.NORD = nord


class waveform(WaveformBase, ProcessDeviceSupportIn):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform'
    _default_     = ()


class waveform_out(WaveformBase, ProcessDeviceSupportOut):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform_out'


# Ensure the .dbd file is loaded.
dbLoadDatabase(os.path.join(os.environ['HERE'], 'dbd/device.dbd'), None, None)
