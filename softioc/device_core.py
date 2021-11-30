from __future__ import print_function

import sys
from . import imports
from .fields import RecordFactory
from ctypes import *


# Black magic lifted from six.py (http://pypi.python.org/pypi/six/) to replace
# use of __metaclass__ for metaclass definition
def with_metaclass(meta, *bases):
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})


class InitClass(type):
    def __new__(cls, name, bases, dict):
        if '__init_class__' in dict:
            dict['__init_class__'] = classmethod(dict['__init_class__'])
        return type.__new__(cls, name, bases, dict)

    def __init__(cls, name, bases, dict):
        type.__init__(cls, name, bases, dict)
        # Binds self.__super.method to the appropriate superclass method
        setattr(cls, '_%s__super' % name.lstrip('_'), super(cls))
        # Binds cls.__super_cls().method to the appropriate superclass
        # class method.  Unfortunately the .__super form doesn't work
        # with class methods, only instance methods.
        setattr(
            cls, '_%s__super_cls' % name,
            classmethod(lambda child: super(cls, child)))
        # Finally call the class initialisatio nmethod.
        cls.__init_class__()

class DeviceCommon(with_metaclass(InitClass)):
    '''Adds support for an __init_class__ method called when the class or any
    of its subclasses is constructed.  Also adds auto-super functionality
    (see iocbuilder.support.autosuper).'''

    def __init_class__(cls): pass

    # By requiring that DeviceCommon be a common base class for the entire
    # Python device hierarchy, we can use this __init__ to test for unused
    # keyword arguments.
    def __init__(self, name, **kargs):
        assert not kargs, \
            'Unused keyword arguments for %s: %s' % (
                name, ', '.join(kargs.keys()))



# Basic dset template used for all record types.  Note that the process
# method isn't generic to all records, so isn't included here.
class DSET_BASE(Structure):
    _fields_ = [
        ('number',          c_long),
        ('dev_report',      CFUNCTYPE(c_int, c_int)),
        ('init',            CFUNCTYPE(c_int, c_int)),
        ('init_record',     CFUNCTYPE(c_int, c_void_p)),
        ('get_ioinit_info', CFUNCTYPE(c_int, c_int, c_void_p, c_void_p))]
    # For the four methods above, the numbers below are the offset of the
    # record argument referencing the instance, or -1 if no record is passed
    # or no instance yet exists.
    _record_offsets_ = [-1, -1, -1, 1]



class DeviceSupportCore(DeviceCommon):
    '''Implementation of core record device support including registration
    with EPICS of the device support table.'''

    # The following fields are used for all records.
    __preset_fields = ['DPVT', 'NAME', 'NSTA', 'NSEV', 'TIME']


    # ------------------------------------------------------------------------
    # Generic support for binding subclasses of this class to the EPICS
    # device support layer.  For each registered record type a dset is
    # constructed containing callbacks into this class.  All callbacks which
    # are record specific (apart from init_record which needs special
    # treatment) are then bound to the appropriate class instance and the
    # appropriate method is invoked.

    def __init_class__(cls):
        '''Record support initialisation, called once during class
        initialisation for each sub-class.  This registers record support for
        the specified device name.'''
        if not hasattr(cls, '_record_type_'):
            # If no record type has been specified then we're a base class
            # with nothing to do.
            return

        # Create an empty device directory.
        # (Potentially this belongs in a mix-in for resolving the linkage
        # between record and instances, but for now this is hard-wired here.)
        cls.__device_directory = {}

        # Convert the list of fields into a dictionary suitable for record
        # lookup.
        fields = set([cls._link_] + cls.__preset_fields + cls._fields_)
        cls.__fields = RecordFactory(cls._record_type_, list(fields))

        # Now construct the device support table.  We build on the common
        # base and add any device specific definitions here.
        class DSET(DSET_BASE):
            _fields_ = cls._dset_extra_[0]
            _record_offsets_ = cls._dset_extra_[1]
        dset = DSET(
            number = len(DSET_BASE._fields_) + len(DSET._fields_) - 1)

        # Check for implementations for all the dset methods.
        zip_list = \
            list(zip(DSET_BASE._fields_[1:], DSET_BASE._record_offsets_)) + \
            list(zip(DSET._fields_, DSET._record_offsets_))
        for (method_name, method_type), record_offset in zip_list:
            method = getattr(cls, '_' + method_name, None)
            if method:
                # Convert each implemented method into a suitable callback
                # function and add it to the dset we're about to publish.
                callback = method_type(
                    cls.__create_method(method, record_offset))
                setattr(dset, method_name, callback)

        # Hang onto the values we publish to EPICS to ensure that they persist!
        # We also need to ensure that the device name persists.
        cls.__dset = dset
        cls._device_name_ = cls._device_name_.encode()
        imports.registryDeviceSupportAdd(cls._device_name_, byref(cls.__dset))


    @classmethod
    def __create_method(cls, method, record_offset):
        '''Creates a callable function that can be set as a dset callback.'''
        if record_offset < 0:
            # If no record offset is specified then we can just return the
            # bound class method we've been passed.
            return method
        else:
            # Methods with bound records need further processing when the
            # call occurs.  We return a closure so that entry point
            # processing can be done when we're called.
            return lambda *args: \
                cls.__call_instance_method(method, args, record_offset)

    @classmethod
    def __call_instance_method(cls, method, args, record_offset):
        '''This is called directly from EPICS as part of record processing.
        At this point we are bound to the class (through the closure created
        by __create_method() above), but not to the instance.  We find the
        instance in the record and dispatch to the bound instance method here.
        '''
        # Convert the raw record pointer into a wrapped record and try to
        # find the associated instance.
        record = cls.__fields(args[record_offset])
        self = record.DPVT
        if self is None:
            print('Record', record.NAME, 'called with no binding')
            return 1
        else:
            args = list(args)
            args[record_offset] = record
            self = cast(self, py_object).value
            return method(self, *args)



    # ------------------------------------------------------------------------
    # Device support: implementations of the generic dset entries.

    @classmethod
    def _init(cls, after):
        '''This routine is called by the record support layer during both
        before and after device initialisation.'''
        return 0

    @classmethod
    def _init_record(cls, record):
        '''This is called for each new record.  We bind the record to its
        instance and call any local initialisation.'''
        record = cls.__fields(record)
        # Here we ask for an instance of the record.  It's the responsibility
        # of the subclass to provide a suitable implementation here.
        self = cls.LookupRecord(getattr(record, cls._link_))

        record.DPVT = id(self)
        self._record = record
        self.name = record.NAME
        return self.init_record(record)

    def __init__(self, name, **kargs):
        # We won't initialise the IOSCANPVT until it's actually requested by
        # a call to get_ioinit_info.  This is only a trivial attempt to
        # reduce resource consumption.
        self.__ioscanpvt = imports.IOSCANPVT()
        self.__super.__init__(name, **kargs)


    def init_record(self, record):
        '''Default record initialisation finalisation.  This can be overridden
        to provide a different return value, or to perform further work on
        record initialisation.'''
        return 0

    def _get_ioinit_info(self, cmd, record, ppvt):
        '''Implements support for I/O Intr scan type.'''
        if not self.__ioscanpvt:
            imports.scanIoInit(byref(self.__ioscanpvt))
        cast(ppvt, POINTER(c_void_p))[0] = self.__ioscanpvt
        return 0


    # ------------------------------------------------------------------------
    # General shared class support.

    def process_severity(self, record, severity, alarm):
        '''Support routine to implement alarm processing.'''
        if severity > record.NSEV:
            record.NSEV = severity
            record.NSTA = alarm

    def trigger(self):
        '''Call this to trigger processing for records with I/O Intr scan.'''
        if self.__ioscanpvt:
            imports.scanIoRequest(self.__ioscanpvt)



class RecordLookup(DeviceCommon):
    '''This class implements automatic record registration.'''

    # Directory of all records as they are created.  This is shared among all
    # subclasses.
    _RecordDirectory = {}

    @classmethod
    def LookupRecord(cls, name):
        '''Returns the registered record with given name, or raises KeyError
        if the record was never initialised.'''
        return cls._RecordDirectory[name]

    def __init__(self, name, **kargs):
        assert name not in self._RecordDirectory, \
            'Record %s already registered' % name
        self._name = name
        self._RecordDirectory[name] = self
        self.__super.__init__(name, **kargs)


LookupRecord = RecordLookup.LookupRecord
LookupRecordList = RecordLookup._RecordDirectory.items


__all__ = ['LookupRecord', 'LookupRecordList']
