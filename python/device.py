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


class dbAddr(Structure):
    _fields_ = (
        ("precord", c_void_p),
        ("pfield", c_void_p),
        ("pfldDes", c_void_p),
        ("asPvt", c_void_p),
        ("no_elements", c_long),
        ("field_type", c_short),
        ("field_size", c_short),
        ("special", c_short),
        ("dbr_field_type", c_short))


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
            kargs.pop('initial_value', None),
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
        self._writing_out = True
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
        if self.__validate and not self.__validate(self, value):
            # Asynchronous validation rejects value.  It's up to the
            # validation routine to do any logging.
            return 1
            
        self._value = value
        if self.__on_update:
            self._DeviceCallbackQueue.Signal((self.__on_update, value))
        return 0

    def set(self, value):
        '''Special routine to set the value directly.'''
        dbaddr = dbAddr()
        imports.dbNameToAddr(self._record.NAME, byref(dbaddr))
        datatype, length, array = value_to_dbr(value)
        imports.dbPutField(
            byref(dbaddr), DbrToDbfCode[datatype], array.ctypes.data, length)

    def get(self):
        return self._value

        
cothread.Spawn(ProcessDeviceSupportOut.DeviceCallbackDispatcher)



def _Device(Base, record_type, val_field, **extras):
    '''Wrapper for generating simple records.'''
    class GenericDevice(Base):
        _record_type_ = record_type
        _device_name_ = 'devPython_' + record_type
        _val_field_   = val_field
        _fields_      = ['UDF', val_field]

    GenericDevice.__name__ = record_type
    return GenericDevice

_In  = ProcessDeviceSupportIn
_Out = ProcessDeviceSupportOut

longin      = _Device(_In,  'longin',    'VAL')
longout     = _Device(_Out, 'longout',   'VAL')
bi          = _Device(_In,  'bi',        'RVAL')
bo          = _Device(_Out, 'bo',        'RVAL')
stringin    = _Device(_In,  'stringin',  'VAL')
stringout   = _Device(_Out, 'stringout', 'VAL')
mbbi        = _Device(_In,  'mbbi',      'RVAL')
mbbo        = _Device(_Out, 'mbbo',      'RVAL')


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
    _fields_      = ['UDF', 'VAL']
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
        memmove(record.BPTR, value.ctypes.data_as(c_void_p),
            self.dtype().itemsize * nord)
        record.NORD = nord

        
class waveform(WaveformBase, ProcessDeviceSupportIn):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform'


class waveform_out(WaveformBase, ProcessDeviceSupportOut):
    _record_type_ = 'waveform'
    _device_name_ = 'devPython_waveform_out'


dbLoadDatabase(
    os.path.join(os.path.split(__file__)[0], 'device.dbd'), None, None)
