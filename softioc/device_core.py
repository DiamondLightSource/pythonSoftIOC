from __future__ import print_function

from . import imports
from .fields import RecordFactory
from ctypes import *


class DeviceCommon:
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

    def __init_subclass__(cls):
        '''Record support initialisation, called once during class
        initialisation for each sub-class.  This registers record support for
        the specified device name.'''

        if not hasattr(cls, '_record_type_'):
            # If no record type has been specified then we're a base class
            # with nothing to do.
            return

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
        # CLS: per-field callback registry.
        # Keys are uppercase field names (e.g. "SCAN", "VAL") or the
        # wildcard "*" which matches every field write.
        # Values are lists of callables.
        self.__field_callbacks = {}
        super().__init__(name, **kargs)

    # ---- CLS extension: field-change callbacks ----------------------------

    def on_field_change(self, field, callback):
        '''Register *callback* to be invoked when *field* is written via
        CA or PVA.

        Args:
            field: EPICS field name (e.g. ``"SCAN"``, ``"VAL"``,
                ``"DISA"``), a list of field names
                (e.g. ``["SCAN", "DRVH", "DRVL"]``), or ``"*"`` to
                receive notifications for **every** field write on this
                record.
            callback: ``callback(record_name, field_name, value_string)``
                called after each matching write.  *value_string* is the
                new value formatted by EPICS as a ``DBR_STRING``.

        Multiple callbacks per field are supported; they are called in
        registration order.  The same callable may be registered for
        different fields.

        Note:
            Callbacks fire only for writes originating from Channel
            Access or PV Access clients.  IOC-shell writes (``dbpf``)
            and internal ``record.set()`` calls bypass asTrapWrite and
            will **not** trigger callbacks.
        '''
        if isinstance(field, (list, tuple)):
            for f in field:
                self.on_field_change(f, callback)
            return
        field = field.upper() if field != "*" else "*"
        self.__field_callbacks.setdefault(field, []).append(callback)

    @property
    def field_callbacks(self):
        '''Read-only view of the registered field-change callbacks.

        Returns a dict mapping field names (and ``"*"``) to lists of
        callables.  Modifying the returned dict has no effect on the
        internal registry — use :meth:`on_field_change` to register new
        callbacks.
        '''
        return {k: list(v) for k, v in self.__field_callbacks.items()}

    def remove_field_callback(self, field, callback):
        '''Remove a specific *callback* previously registered for *field*.

        Args:
            field: Field name (e.g. ``"SCAN"``) or ``"*"``.
            callback: The exact callable that was passed to
                :meth:`on_field_change`.

        Raises:
            ValueError: If *callback* is not registered for *field*.
        '''
        field = field.upper() if field != "*" else "*"
        try:
            self.__field_callbacks[field].remove(callback)
        except (KeyError, ValueError):
            raise ValueError(
                f"Callback not registered for field {field!r}")
        # Clean up empty lists to keep the dict tidy.
        if not self.__field_callbacks[field]:
            del self.__field_callbacks[field]

    def clear_field_callbacks(self, field=None):
        '''Remove all field-change callbacks, or all for a single *field*.

        Args:
            field: If ``None`` (default), remove **all** callbacks on
                this record.  Otherwise, remove only those registered for
                the given field name (or ``"*"``).

        Raises:
            KeyError: If *field* is given but has no registered callbacks.
        '''
        if field is None:
            self.__field_callbacks.clear()
        else:
            field = field.upper() if field != "*" else "*"
            try:
                del self.__field_callbacks[field]
            except KeyError:
                raise KeyError(
                    f"No callbacks registered for field {field!r}")

    def _get_field_callbacks(self, field):
        '''Return the list of callbacks for *field*, including wildcards.

        This is an internal helper used by :mod:`~softioc.field_monitor`.
        '''
        cbs = list(self.__field_callbacks.get(field, []))
        cbs.extend(self.__field_callbacks.get("*", []))
        return cbs


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
        '''Trigger immediate record processing.

        Uses scanIoRequest for I/O Intr records (fast path).
        Falls back to scanOnce for records on any other SCAN setting.

        Only one path fires per call: scanIoRequest returns non-zero
        when the record is on the I/O Intr scan list, so scanOnce is
        skipped.  When the record has been moved to a different scan
        list scanIoRequest returns zero and scanOnce takes over.

        Known limitation — periodic SCAN and double processing:

        When SCAN is set to a periodic rate (e.g. "1 second"), the
        EPICS scan thread calls dbProcess on its own schedule, and
        set() also calls scanOnce → dbProcess.  The record is
        processed by both paths.  dbScanLock serialises access and
        recGblCheckDeadband prevents duplicate monitors when the
        value has not changed, so this is harmless in practice but
        does result in extra processing cycles.

        To avoid this, use ``iocInit(auto_reset_scan=True)``.
        The C hook resets SCAN back to I/O Intr after forwarding
        the requested rate to the Python callback, so the record
        stays on the I/O Intr scan list and scanIoRequest remains
        the only processing path.  Passive writes are exempt from
        the reset (they are a deliberate "stop updating" command).
        '''
        queued = False
        if self.__ioscanpvt:
            queued = imports.scanIoRequest(self.__ioscanpvt)
        if not queued and hasattr(self, '_record') \
                and self._record is not None:
            imports.scan_once(self._record.record.value)



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
        super().__init__(name, **kargs)


LookupRecord = RecordLookup.LookupRecord
LookupRecordList = RecordLookup._RecordDirectory.items


__all__ = ['LookupRecord', 'LookupRecordList']
