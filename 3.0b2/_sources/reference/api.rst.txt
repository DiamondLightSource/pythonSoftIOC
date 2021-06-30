.. _API:

API
===

.. automodule:: softioc

    ``softioc``
    -----------

    The top level softioc module contains a number of packages that can be used
    in the creation of IOCs:

    `softioc.softioc`
        This module wraps the basic interface to the EPICS IOC. A large number of
        interactive EPICS commands are wrapped and can be made available through the
        interpreter by invoking the interpreter through this module.

    `softioc.asyncio_dispatcher`
        A dispatcher for `asyncio` based applications instead of the default
        `cothread` one

    `softioc.alarm`
        This module simply contains definitions for severity and alarm values taken
        from the EPICS ``alarm.h`` header file.

    `softioc.builder`
        This module provides facilities for creating PVs.

    `softioc.pvlog`
        The act of importing this module configures the IOC to log every external
        put to the database.

    The following submodules implement internals and should not normally be looked
    at directly:

    ``softioc.imports``
        Imports and wraps C functions from EPICS IOC support.

    ``softioc.fields``
        Used internally as part of record support to implement access to EPICS
        record fields.

    ``softioc.device_core``
        Implements the basics of ``Python`` EPICS device support.

    `softioc.device`
        Implements ``Python`` device support for all the record types supported.

    ``softioc.pythonSoftIoc``
        Implements `epicsdbbuilder` interface for all of the ``Python`` records.

.. data:: softioc.__version__
    :type: str

    Version number as calculated by https://github.com/dls-controls/versiongit

.. automodule:: softioc.softioc

    ..
        NOTE: can't use :members: here as it calls repr on the exit object which
        makes the process exit!

    Top Level IOC Interface: `softioc.softioc`
    ------------------------------------------

    This module provides the following functions for general use (available by
    importing ``*``):

.. autofunction:: iocInit

.. autofunction:: dbLoadDatabase

    .. note::

        This function is not normally called directly, instead
        `softioc.builder.LoadDatabase` is normally used to create and load the
        EPICS database on the fly.

        However, if required, an existing EPICS database can be loaded
        explicitly using this method.  Note that `dbLoadDatabase` cannot be
        called after `iocInit`.

..  autofunction:: devIocStats

..  autofunction:: interactive_ioc

While the interactive shell is running a number of EPICS test functions are made
available for use together with the constant value `exit` with special
behaviour: typing `exit` at the interpreter prompt will immediately call
``epicsExit`` causing the Python interpreter and IOC to terminate.

This module provides Python wrappers for the following EPICS test functions and
makes them available to the `interactive_ioc` interpreter shell. See the `IOC
Test Facilities`_ documentation for more details of each function.

.. _IOC Test Facilities:
    https://docs.epics-controls.org/en/latest/appdevguide/IOCTestFacilities.html

..  autofunction:: dba
..  autofunction:: dbl
..  autofunction:: dbnr
..  autofunction:: dbgrep
..  autofunction:: dbgf
..  autofunction:: dbpf
..  autofunction:: dbpr
..  autofunction:: dbtr
..  autofunction:: dbtgf
..  autofunction:: dbtpf
..  autofunction:: dbior
..  autofunction:: dbhcr
..  autofunction:: gft
..  autofunction:: pft
..  autofunction:: tpn
..  autofunction:: dblsr
..  autofunction:: dbLockShowLocked
..  autofunction:: scanppl
..  autofunction:: scanpel
..  autofunction:: scanpiol
..  autofunction:: generalTimeReport
..  autofunction:: eltc

..  attribute:: exit

    Displaying this value will invoke ``epicsExit()`` causing the IOC to
    terminate immediately.

.. automodule:: softioc.asyncio_dispatcher
    :members:

    Asyncio Dispatcher: `softioc.asyncio_dispatcher`
    ------------------------------------------------

    If your application uses `asyncio` then this module gives an alternative
    dispatcher for caput requests.

.. automodule:: softioc.builder

    Creating Records: `softioc.builder`
    -----------------------------------

    This module publishes functions for creating records.  All of the other methods
    in this module must be called before calling :func:`LoadDatabase`, after which
    no function in this module is usable.

    See `softioc.device` for a detailed explanation of record support and creation,
    but note that only the following records types have direct support from this
    module:

        ai, ao, bi, bo, longin, longout, mbbi, mbbo, stringin, stringout, waveform

    The following methods create records of the corresponding type.  For all records
    the `initial_value` parameter can be used to specify an initial value for the
    record.

    The following optional keyword arguments are available for all of these
    functions:

    .. _initial_value:

    `initial_value`
    ~~~~~~~~~~~~~~~

    This is used to specify an initial value for each record.

    .. _on_update:

    `on_update`
    ~~~~~~~~~~~

    This is only available on OUT records (including those created by
    :func:`WaveformOut`).  This specifies a function that will be called after
    record processing has completed.

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

    .. _on_update_name:

    `on_update_name`
    ~~~~~~~~~~~~~~~~

    This is an alternative form of `on_update` with the same behaviour: note
    that at most one of `on_update` and `on_update_name` may be passed.  The
    difference is that `on_update_name` is called with the record name as its
    second argument after the value as the first argument.

    .. _validate:

    `validate`
    ~~~~~~~~~~

    Also only available on OUT records, specifies a function called during
    record processing. If used this should be set to a callable taking two
    arguments.  The first argument will be the record object, and the second
    will be the new value being written.  The `validate` function can reject
    the update by returning `False` or accept it by returning `True`.

    .. note::

        This function is called asynchronously on a thread determined by
        EPICS and it is not safe to perform any cothread actions within this
        callback.

    .. _always_update:

    `always_update`
    ~~~~~~~~~~~~~~~

    Again only on OUT records, determines whether record writes which don't
    change the existing value are passed through.  If this field is not set then
    writing to ``.PROC`` will have no visible effect.

    This flag defaults to `False`, in which case updates to the record
    which don't change its value will be discarded.  In particular this means
    that such updates don't call `validate` or `on_update`.

For all of these functions any EPICS database field can be assigned a value by
passing it as a keyword argument for the corresponding field name (in upper
case) or by assigning to the corresponding field of the returned record object.
Thus the ``**fields`` argument in all of the definitions below refers to both the
optional keyword arguments listed above and record field names.

All functions return a wrapped `ProcessDeviceSupportIn` or
`ProcessDeviceSupportOut` instance.

..  function::
        aIn(name, LOPR=None, HOPR=None, **fields)
        aOut(name, LOPR=None, HOPR=None, **fields)

    Create ``ai`` and ``ao`` records.  The lower and upper limits for the
    record can be specified, and if specified these will also be used to set the
    ``EGUL`` and ``EGUF`` fields.

..  function::
        boolIn(name, ZNAM=None, ONAM=None, **fields)
        boolOut(name, ZNAM=None, ONAM=None, **fields)

    Create ``bi`` and ``bo`` records with the specified names for false (zero)
    and true (one).

..  function::
        longIn(name, LOPR=None, HOPR=None, EGU=None, **fields)
        longOut(name, DRVL=None, DRVH=None, EGU=None, **fields)

    Create ``longin`` and ``longout`` records with specified limits and units.

..  function::
        stringIn(name, **fields)
        stringOut(name, **fields)

    Create ``stringin`` and ``stringout`` records.

..  function::
        mbbIn(name, *options, **fields)
        mbbOut(name, *options, **fields)

    Create ``mbbi`` and ``mbbo`` records.  Up to 16 options can be specified as
    either an option name or a tuple of tw fields.  The name or first field of
    the tuple names the option, and the second optional field is the option
    severity.  For example::

        status = mbbIn('STATUS',
            'OK',
            ('FAILING', alarm.MINOR_ALARM),
            ('FAILED', alarm.MAJOR_ALARM))

    Numerical values are assigned to options sequentially from 0 to 15 and
    cannot be overridden.

    ..  warning::
        This is a strictly incompatible change from version 2, but is now
        compatible with version 2 of epics_device_.

..  function::
        Waveform(name, [value,] **fields)
        WaveformOut(name, [value,] **fields)

    Create ``waveform`` records.  Depending on whether `Waveform` or
    `WaveformOut` is called the record is configured to behave as an IN or an
    OUT record, in particular `on_update` can only be specified when calling
    `WaveformOut`.

    If ``value`` is specified or if an `initial_value` is specified (only one of
    these can be used) the value is used to initialise the waveform and to
    determine its field type and length.  If no initial value is specified then
    the keyword argument ``length`` must be used to specify the length of the
    waveform.

    The field type can be explicitly specified either by setting the ``datatype``
    keyword to a Python type name, or by setting ``FTVL`` to the appropriate EPICS
    field type name.  Otherwise the field type is taken from the initial value
    if given, or defaults to ``'FLOAT'``.


The following function generates a specialised record.

..  function:: Action(name, **fields)

    Creates a record (using `boolOut`) which will always call the `on_update`
    method when processed.  Used for action records.  The `on_update` keyword
    should always be passed.


The following functions manage record names.  The record device name must be
specified before creating records, then each record will be created with a
standard two part name of the form ``device:name`` where the ``device`` part is
specified by the functions below and the ``name`` part is specified in the
record creation function.

..  function:: SetDeviceName(device_name)

    Sets up the prefix part of the record name, referred to here as the "device"
    part.  This function must be called before creating any records.
    Note that
    only this function need be used, the three other functions below are
    entirely optional.

..  function:: UnsetDevice()

    This can optionally be called after completing the creation of records to
    prevent the accidential creation of records with the currently set device
    name.


The following helper functions are useful when constructing links between
records.

..  function::
        PP(record)
        CP(record)
        NP(record)
        MS(record)

    When assigned to a link field in a record these functions add the
    appropriate processing attributes to the link.  These are not normally used.


The following attributes allow more direct access to record creation.

..  attribute:: records

    This is the ``iocbuilder`` records object, and is populated with
    functions named after each available record type.  Records created with
    these calls are created with soft device support and Python is not involved
    in their processing.

    The following example shows a calc record being used to post-process a
    standard Python IOC record::

        from softioc import builder
        builder.SetDeviceName('XX-XX-XX-01')
        rec = aIn('VALUE')
        calc = records.calc('CALC', CALC = 'A*B', A = rec, B = 42)
        rec.FLNK = PP(calc)


Finally, the following function is used to load record definitions before
starting the IOC.

..  function:: LoadDatabase()

    This must be called exactly once after creating all the records required by
    the IOC and before calling :func:`~softioc.softioc.iocInit`.  After this
    function has been called none of the functions provided by
    :mod:`softioc.builder` are usable.

.. automodule:: softioc.alarm

    Alarm Value Definitions: `softioc.alarm`
    ----------------------------------------


The following values can be passed to IN record :meth:`~softioc.device.ProcessDeviceSupportIn.set` and
:meth:`~softioc.device.ProcessDeviceSupportIn.set_alarm` methods.

..  attribute::
        NO_ALARM = 0
        MINOR_ALARM = 1
        MAJOR_ALARM = 2
        INVALID_ALARM = 3

    These are severity values.  The default severity is ``NO_ALARM``.

..  attribute::
        READ_ALARM
        WRITE_ALARM
        HIHI_ALARM
        HIGH_ALARM
        LOLO_ALARM
        LOW_ALARM
        STATE_ALARM
        COS_ALARM
        COMM_ALARM
        TIMEOUT_ALARM
        HW_LIMIT_ALARM
        CALC_ALARM
        SCAN_ALARM
        LINK_ALARM
        SOFT_ALARM
        BAD_SUB_ALARM
        UDF_ALARM
        DISABLE_ALARM
        SIMM_ALARM
        READ_ACCESS_ALARM
        WRITE_ACCESS_ALARM

    Alarm code definitions.  Frankly these values aren't terribly useful, only
    the severity is used for most notifications, but an alarm code needs to be
    specified when specifying a non zero severity.


.. automodule:: softioc.pvlog

    Automatic PV logging: `softioc.pvlog`
    -------------------------------------

    Once this module has been imported all channel access writes to any PV published
    by this IOC will be logged by writing a suitable message to stdout.  There is
    currently no control or customisation of this feature.

.. automodule:: softioc.device

    Record Support in the Python Soft IOC: `softioc.device`
    -------------------------------------------------------

The Python soft IOC implements EPICS device support (almost) entirely in Python.
This is used to invoke Python processing in response to record processing,
making it easy to integrate Python into the EPICS IOC layer.

Records are created dynamically during IOC startup before calling
:func:`~softioc.softioc.iocInit` and with the help of the `softioc.builder`
module can be loaded with :func:`~softioc.builder.LoadDatabase`.

All records are created internally using methods of the ``PythonDevice``
class, one method for each of the supported record types, however the
corresponding wrapping functions published by `softioc.builder` should be
used as they configure sensible defaults and are generally easier to use.

Create IN records (used for publishing data *from* the IOC, the naming of the
direction is confusing) using the following `softioc.builder` methods:

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
~~~~~~~~~~~~~~~~~~~~~~~

EPICS IN records are implemented as subclasses of the `ProcessDeviceSupportIn`
class which provides the methods documented below.

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
~~~~~~~~~~~~~~~~~~~~~~~~

..  class:: ProcessDeviceSupportOut

    This class is used to implement Python device support for the record types
    ``ao``, ``bo``, ``longout``, ``mbbo`` and OUT ``waveform`` records.  All OUT
    records support the following methods.

    ..  method:: set(value, process=True)

        Updates the value associated with the record.  By default this will
        trigger record processing, and so will cause any associated `on_update`
        and `validate` methods to be called.  If ``process`` is `False`
        then neither of these methods will be called, but the value will still
        be updated.

    ..  method:: get()

        Returns the value associated with the record.

.. _epics_device: https://github.com/Araneidae/epics_device
