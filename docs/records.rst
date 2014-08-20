.. _records:

Record Support in the Python Soft IOC
=====================================

..  module:: softioc.device
    :synopsis: Implementation of Python Device support


The Python soft IOC implements EPICS device support (almost) entirely in Python.
This is used to invoke Python processing in response to record processing,
making it easy to integrate Python into the EPICS IOC layer.

Records are created dynamically during IOC startup before calling
:func:`iocInit` and with the help of the :mod:`softioc.builder` module can be
loaded with :func:`~softioc.builder.LoadDatabase`.

All records are created internally using methods of the :class:`PythonDevice`
class, one method for each of the supported record types, however the
corresponding wrapping functions published by :mod:`softioc.builder` should be
used as they configure sensible defaults and are generally easier to use.

Create IN records (used for publishing data *from* the IOC, the naming of the
direction is confusing) using the following :mod:`softioc.builder` methods:

    :func:`~softioc.builder.aIn`, :func:`~softioc.builder.boolIn`,
    :func:`~softioc.builder.longIn`, :func:`~softioc.builder.stringIn`,
    :func:`~softioc.builder.mbbIn`, :func:`~softioc.builder.Waveform`.

Create OUT records for receiving control information into the IOC using the
following methods:

    :func:`~softioc.builder.aOut`, :func:`~softioc.builder.boolOut`,
    :func:`~softioc.builder.longOut`, :func:`~softioc.builder.stringOut`,
    :func:`~softioc.builder.mbbOut`, :func:`~softioc.builder.WaveformOut`.

For all records the `initial_value` keyword argument can be used to specify the
records value on startup.


Working with IN records
-----------------------

EPICS IN records are implemented as subclasses of the
:class:`ProcessDeviceSupportIn` class which provides the methods documented
below.

..  class:: ProcessDeviceSupportIn

    This class is used to implement Python device support for the record types
    ``ai``, ``bi``, ``longin``, ``mbbi`` and IN ``waveform`` records.

    ..  method:: set(value, severity=NO_ALARM, alarm=UDF_ALARM, timestamp=None)

        Updates the stored value and severity status and triggers an update.  If
        ``SCAN`` has been set to ``'I/O Intr'`` (which is the default if the
        :mod:`~softioc.builder` methods have been used) then the record will be
        processed by EPICS and the given value will be published to all users.

        Optionally an explicit timestamp can be set.  This is a value in seconds
        in the Unix epoch, as returned by :func:`time.time`.  This argument only
        has any effect if ``TSE = -2`` was set when the record was created.

        Note that when calling :func:`set` for a waveform record the value is
        always copied immediately -- this avoids accidents with mutable values.

    ..  method:: set_alarm(severity, alarm, timestamp=None)

        This is exactly equivalent to calling::

            rec.set(rec.get(), severity, alarm, timestamp)

        and triggers an alarm status change without changing the value.

    ..  method:: get()

        This returns the value last written to this record with :func:`set`.

        Note that channel access puts to a Python soft IOC input record are
        completely ineffective, and this includes waveform records.


Working with OUT records
------------------------

When creating OUT records three further optional keyword arguments can be
specified:

`on_update`
    If used this should be set to a callable taking exactly one argument.  After
    successful record processing this function will be called with the new value
    just written to the record.

    Note that this callback occurs at an unpredictable time after record
    processing and if repeated high speed channel access puts are in progress it
    is possible that callbacks may be delayed.  Each callback will be passed the
    value at the time the record was processed.

    Note also that `on_update` callbacks occur as part of cothread processing
    and normal cothread operations can occur during the callback.  However only
    one callback is dispatched at a time, so if a callback blocks it will delay
    `on_update` callbacks for other records.

`validate`
    If used this should be set to a callable taking two arguments.  The first
    argument will be the record object, and the second will be the new value
    being written.  The `validiate` function can reject the update by returning
    :const:`False` or accept it by returning :const:`True`.

    Note that this function is called asynchronously on a thread determined by
    EPICS and it is not safe to perform any cothread actions within this
    callback.

`always_update`
    This flag defaults to :const:`False`, in which case updates to the record
    which don't change its value will be discarded.  In particular this means
    that such updates don't call `validate` or `on_update`.

..  class:: ProcessDeviceSupportOut

    This class is used to implement Python device support for the record types
    ``ao``, ``bo``, ``longout``, ``mbbo`` and OUT ``waveform`` records.  All OUT
    records support the following methods.

    ..  method:: set(value, process=True)

        Updates the value associated with the record.  By default this will
        trigger record processing, and so will cause any associated `on_update`
        and `validate` methods to be called.  If `process` is :const:`False`
        then neither of these methods will be called, but the value will still
        be updated.

    ..  method:: get()

        Returns the value associated with the record.
