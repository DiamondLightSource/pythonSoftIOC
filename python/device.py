import os
import time
from ctypes import *
import numpy
import cothread

import alarm
from fields import DbfCodeToNumpy
from imports import dbLoadDatabase, recGblResetAlarms
from device_core import DeviceSupportCore, RecordLookup



class ProcessDeviceSupport(DeviceSupportCore, RecordLookup):
    '''Implements canonical default processing for records with a _process
    method.  Processing typically either copies a locally set value into the
    record, or else reads a value from the record and triggers an update.
    '''

    # Most records just have an extra process method, but unfortunately ai/ao
    # will have to override this to also add their special_linconv method.
    _dset_extra_ = ([('process', CFUNCTYPE(c_int, c_void_p))], [0])

    # This queue is used to communicate process update events to a receiving
    # cothread.  A single dispatching process is spawned to consume updates
    # and convert them into synchronous method calls.
    _DeviceCallbackQueue = cothread.ThreadedEventQueue()
    @classmethod
    def DeviceCallbackDispatcher(cls):
        while True:
            callback, value = cls._DeviceCallbackQueue.Wait()
            callback(value)
            
    def __init__(self, name, **kargs):
        # Note that update and validate methods are only valid for input
        # records.
        self.__on_update = kargs.pop('on_update', None)
        self.__validate  = kargs.pop('validate', None)

        # We implement update locking via a simple trick which relies on the
        # Python global interpreter lock: this ensures that assigning or
        # reading a single value is atomic.  We therefore cluster all our
        # variable state into a single tuple which represents a single value
        # to be processed.
        #    The tuple contains everything needed to be written: the value,
        # severity, alarm and optional timestamp.
        self._value = (
            kargs.pop('initial_value', None),   # Value
            alarm.NO_ALARM, alarm.UDF_ALARM,    # Severity and alarm
            None)                               # Timestamp
        self.__super.__init__(name, **kargs)
        
    def init_record_out(self, record):
        '''Special record initialisation for out records only: implements
        special record initialisation if an initial value has been specified,
        allowing out records to have a sensible initial value.'''
        _value = self._value
        if _value[0] is not None:
            # For out record initialisation we do something special: if an
            # initial value has already been specified then we simulate a
            # full record process to cause the record to update -- this
            # allows a configuration record to be initialised from the
            # driver.
            self.process_in(record, _value)
            if _value[3] is None:
                # Synthesise a timestamp if no timestamp already given
                record.TIME = time.time()
            record.UDF = 0
            recGblResetAlarms(record)
            self.value = _value[0]
        return 0

    def process_out(self, record):
        '''Processing suitable for output records.  Performs immediate value
        validation and asynchronous update notification.'''
        value = self._read_value(record)
        if self.__validate and not self.__validate(value):
            # Asynchronous validation rejects value.  It's up to the
            # validation routine to do any logging.
            return 1
        self.value = value
        if self.__on_update:
            self._DeviceCallbackQueue.Signal((self.__on_update, value))
        return 0

    def process_in(self, record, _value=None):
        # For input process we copy the value stored in the instance to the
        # record.  The alarm status is also updated, and a custom timestamp
        # can also be set.
        #    We leave the original value unchanged so that further processing
        # can safely be triggered.
        if _value is None:
            _value = self._value
        value, severity, alarm, timestamp = _value
        self._write_value(record, value)
        self.process_severity(record, severity, alarm)
        if timestamp is not None:
            record.TIME = timestamp
        return 0

    # Default implementations of read and write, overwritten where necessary.
    def _read_value(self, record):
        return getattr(record, self._val_field_)
    def _write_value(self, record, value):
        setattr(record, self._val_field_, value)
        

    def set_on_update(self, on_update):
        '''Registered the given callback function to be invoked each time a
        value is written to the record.'''
        self.__on_update = on_update
    def set_validate(self, validate):
        '''Registers an asynchronous validation function to be invoked to
        filter each value written to the record.'''
        self.__validate = validate
        
    def set_severity(self,
            severity=alarm.NO_ALARM, alarm=alarm.UDF_ALARM, timestamp=None):
        '''Set the severity and alarm reason to be reported next time the
        record processes.'''
        value = self._value[0]
        self._value = (value, severity, alarm, timestamp)
        self.trigger()
    def set(self, value,
            severity=alarm.NO_ALARM, alarm=alarm.UDF_ALARM, timestamp=None):
        '''Updates the stored value and triggers an update.  The alarm
        severity and timestamp can also be specified if appropriate.'''
        self._value = (value, severity, alarm, timestamp)
        self.value = value
        self.trigger()

    def get(self):
        '''Returns the last written value.'''
        return self.value

cothread.Spawn(ProcessDeviceSupport.DeviceCallbackDispatcher)



def _Device(in_out, record_type, val_field, **extras):
    '''Wrapper for generating simple records.'''
    class GenericDevice(ProcessDeviceSupport):
        _record_type_ = record_type
        _device_name_ = 'devPython_' + record_type
        _val_field_   = val_field
        _fields_      = ['UDF', val_field]

        if in_out == 'in':
            _link_ = 'INP'
            _process = ProcessDeviceSupport.process_in
        if in_out == 'out':
            _link_ = 'OUT'
            _process = ProcessDeviceSupport.process_out
            init_record = ProcessDeviceSupport.init_record_out

    GenericDevice.__name__ = record_type
    return GenericDevice


longin      = _Device('in',  'longin',    'VAL')
longout     = _Device('out', 'longout',   'VAL')
bi          = _Device('in',  'bi',        'RVAL')
bo          = _Device('out', 'bo',        'RVAL')
stringin    = _Device('in',  'stringin',  'VAL')
stringout   = _Device('out', 'stringout', 'VAL')
mbbi        = _Device('in',  'mbbi',      'RVAL')
mbbo        = _Device('out', 'mbbo',      'RVAL')


NO_CONVERT = 2

dset_process_linconv = (
    [('process',         CFUNCTYPE(c_int, c_void_p)),
     ('special_linconv', CFUNCTYPE(c_int, c_void_p, c_int))],
    [0, 0])

# For ai and ao there's no point in supporting RVAL <-> VAL conversion, so
# for these we support no conversion directly.

class ai(ProcessDeviceSupport):
    _record_type_ = 'ai'
    _link_        = 'INP'
    _device_name_ = 'devPython_ai'
    _val_field_   = 'VAL'
    _fields_      = ['UDF', 'VAL']
    _dset_extra_  = dset_process_linconv

    def _process(self, record):
        _value = self._value
        self.process_in(record, _value)
        # Because we're returning NO_CONVERT we need to do the .UDF updating
        # ourself (otherwise the record support layer does this).
        record.UDF = int(numpy.isnan(_value[0]))
        return NO_CONVERT
        

class ao(ProcessDeviceSupport):
    _record_type_ = 'ao'
    _link_        = 'OUT'
    _device_name_ = 'devPython_ao'
    _val_field_   = 'VAL'
    _fields_      = ['UDF', 'VAL']
    _dset_extra_  = dset_process_linconv

    def init_record(self, record):
        self.init_record_out(record)
        return NO_CONVERT

    _process = ProcessDeviceSupport.process_out


# The waveform class is rather special, as the same record type is used to
# support both input and output records.

class waveform(ProcessDeviceSupport):
    _record_type_ = 'waveform'
    _link_ = 'INP'
    _device_name_ = 'devPython_waveform'
    # In the waveform record class, the following four fields are key:
    #   FTVL    Type of stored waveform (as a DBF_ code)
    #   BPTR    Pointer to raw array containing waveform data
    #   NELM    Length of allocated array in number of elements
    #   NORD    Currently reported length of array (0 <= NORD <= NELM)
    _fields_ = ['UDF', 'FTVL', 'BPTR', 'NELM', 'NORD']


    def __init__(self, name, **kargs):
        self.out_rec = kargs.pop('out', False)
        self.__super.__init__(name, **kargs)

    def init_record(self, record):
        self.dtype = DbfCodeToNumpy[record.FTVL]
        if self.out_rec:
            return self.init_record_out(record)
        return 0
    
    def _process(self, record):
        if self.out_rec:
            return self.process_out(record)
        else:
            return self.process_in(record)

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


dbLoadDatabase(
    os.path.join(os.path.split(__file__)[0], 'device.dbd'), None, None)
