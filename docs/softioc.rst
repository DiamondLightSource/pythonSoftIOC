.. _softioc:

Soft IOC Python Module
======================

..  module:: softioc
    :synopsis: Top level module of Python Soft IOC facilities


The :mod:`softioc` module is an integral part of the Python soft IOC server
``pythonIoc``.  Its path is automatically available to the interpreter and the
following submodules can be loaded:

:mod:`softioc.softioc`
    This module wraps the basic interface to the EPICS IOC.  A large number of
    interactive EPICS commands are wrapped and can be made available through the
    interpreter by invoking the interpreter through this module.

:mod:`softioc.alarm`
    This module simply contains definitions for severity and alarm values taken
    from the EPICS ``alarm.h`` header file.

:mod:`softioc.builder`
    This module provides facilities for creating PVs.

:mod:`softioc.pvlog`
    The act of importing this module configures the IOC to log every external
    put to the database.


The following submodules implement internals and should not normally be looked
at directly:

:mod:`softioc.imports`
    Imports and wraps C functions from EPICS IOC support.

:mod:`softioc.fields`
    Used internally as part of record support to implement access to EPICS
    record fields.

:mod:`softioc.device_core`
    Implements the basics of ``Python`` EPICS device support.

:mod:`softioc.device`
    Implements ``Python`` device support for all the record types supported.

:mod:`softioc.pythonSoftIoc`
    Implements :mod:`iocbuilder` interface for all of the ``Python`` records.


Top Level IOC Interface: :mod:`softioc.softioc`
-----------------------------------------------

..  module:: softioc.softioc
    :synopsis: Interface to IOC creation and startup functionality


This module provides the following functions for general use (available by
importing ``*``):

..  function:: iocInit()

    This must be called exactly once after loading all EPICS database files.
    After this point the EPICS IOC is running and serving PVs.

..  function:: dbLoadDatabase(database, path=None, substitutions=None)

    This loads the specified EPICS database into the IOC with any given
    substitutions.  Note that this function is not normally called directly,
    instead :mod:`softioc.builder` and its :func:`~softioc.builder.LoadDatabase`
    method is normally used to create and load the EPICS database on the fly.

    However, if required, an existing EPICS database can be loaded explicitly
    using this method.  Note that :func:`dbLoadDatabase` cannot be called after
    :func:`iocInit`.

..  function:: devIocStats(ioc_name)

    This will load a template for the devIocStats library with the specified IOC
    name.  This should be called before :func:`iocInit`.

..  function:: interactive_ioc(context={}, call_exit=True)

    This is the normal way to run an interactive shell after starting the IOC.
    The `context` argument is a dictionary of values that will be made available
    to the interactive Python shell together with a number of EPICS test
    functions.  By default, if `call_exit` is :const:`True`, the IOC will be
    terminated by calling :func:`epicsExit` when the interpreter exits, which
    means that :func:`interactive_ioc` will not return.

    While the interactive shell is running a number of EPICS test functions are
    made available for use together with the constant value :const:`exit` with
    special behaviour: typing :const:`exit` at the interpreter prompt will
    immediately call :func:`epicsExit` causing the Python interpreter and IOC to
    terminate.

This module provides Python wrappers for the following EPICS test functions and
makes them available to the :func:`interactive_ioc` interpreter shell.  See the
EPICS documentation for more details of each function.

..  function:: dba(field)

    Prints value of each field in dbAddr structure associated with field.

..  function:: dbl(pattern='', fields='')

    Prints the names of records in the database matching pattern.  If
    a (space separated) list of fields is also given then the values of
    the fields are also printed.

..  function:: dbnr(all=0)

    Print number of records of each record type.

..  function:: dbgrep(pattern)

    Lists all record names that match the pattern.  '*' matches any number of
    characters in a record name.

..  function:: dbgf(field)

    Prints field type and value.

..  function:: dbpf(field, value)

    Writes the given value into the field.

..  function:: dbpr(record, interest=0)

    Prints all the fields in record up to the indicated interest level:

    = ===========================
    0 Application fields which change during record processing
    1 Application fields which are fixed during processing
    2 System developer fields of major interest
    3 System developer fields of minor interest
    4 All other fields.
    = ===========================

..  function:: dbtr(record)

    Tests processing of the specified record.

..  function:: dbior(driver='', interest=0)

    Prints driver reports for the selected driver (or all drivers if
    driver is omitted) at the given interest level.

..  function:: dbhcr()

    Prints hardware configuration report.

..  function:: scanppl(rate=0.0)

    Prints all records with the selected scan rate (or all if rate=0).

..  function:: scanpel(event=0)

    Prints all records with selected event number (or all if event=0).

..  function:: scanpiol()

    Prints all records in the I/O event scan lists.

..  function:: generalTimeReport(level=0)

    Displays time providers and their status

..  function:: eltc(enable)

    Turn EPICS logging on or off.

..  function::
        dbLockShowLocked()
        dblsr()
        dblsr()
        dbtgf()
        dbtpf()
        dbtpn()
        gft()
        pft()
        tpn()

    These are all wrappers around the corresponding EPICS function, see the
    EPICS documentation for details of their meaning and behaviour.

..  attribute:: exit

    Displaying this value will invoke :func:`epicsExit` causing the IOC to
    terminate immediately.


Creating Records: :mod:`softioc.builder`
----------------------------------------

..  module:: softioc.builder
    :synopsis: Tools for building Python bound PVs


This module publishes functions for creating records.  All of the other methods
in this module must be called before calling :func:`LoadDatabase`, after which
no function in this module is usable.

See :ref:`records` for a detailed explanation of record support and creation,
but note that only the following records types have direct support from this
module:

    ai, ao, bi, bo, longin, longout, mbbi, mbbo, stringin, stringout, waveform

The following methods create records of the corresponding type.  For all records
the `initial_value` parameter can be used to specify an initial value for the
record.

The following optional keyword arguments are available for all of these
functions:

`initial_value`
    This is used to specify an initial value for each record.

`on_update`
    This is only available on OUT records (including those created by
    :func:`WaveformOut`).  This specifies a function that will be called after
    record processing has completed.

`validate`
    Also only available on OUT records, specifies a function called during
    record processing.  Note that this function is not cothread safe, that is to
    say, it is not called on the cothread thread.

`always_update`
    Again only on OUT records, determines whether record writes which don't
    change the existing value are passed through.  If this field is not set then
    writing to ``.PROC`` will have no visible effect.

For all of these functions any EPICS database field can be assigned a value by
passing it as a keyword argument for the corresponding field name (in upper
case) or by assigning to the corresponding field of the returned record object.
Thus the `**fields` argument in all of the definitions below refers to both the
optional keyword arguments listed above and record field names.

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
        mbbIn(name, *option_values, **fields)
        mbbOut(name, *option_values, **fields)

    Create ``mbbi`` and ``mbbo`` records.  Up to 16 options can be specified as
    a list of two or three field tuples.  The first field of each tuple is the
    option name, the second field is the option value, and the third optional
    field is the option severity.  For example::

        status = mbbIn('STATUS',
            ('OK', 0),
            ('FAILING', 1, alarm.MINOR_ALARM),
            ('FAILED', 2, alarm.MAJOR_ALARM))

..  function::
        Waveform(name, [value,] **fields)
        WaveformOut(name, [value,] **fields)

    Create ``waveform`` records.  Depending on whether :func:`Waveform` or
    :func:`WaveformOut` is called the record is configured to behave as an IN or
    an OUT record, in particular `on_update` can only be specified when calling
    :func:`WaveformOut`.

    If `value` is specified or if an `initial_value` is specified (only one of
    these can be used) the value is used to initialise the waveform and to
    determine its field type and length.  If no initial value is specified then
    the keyword argument `length` must be used to specify the length of the
    waveform.

    The field type can be explicitly specified either by setting the `datatype`
    keyword to a Python type name, or by setting `FTVL` to the appropriate EPICS
    field type name.  Otherwise the field type is taken from the initial value
    if given, or defaults to ``'FLOAT'``.


The following function generates a specialised record.

..  function:: Action(name, **fields)

    Creates a record (using :func:`boolOut`) which will always call the
    `on_update` method when processed.  Used for action records.  The
    `on_update` keyword should always be passed.


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

    This is the :mod:`iocbuilder` records object, and is populated with
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


Alarm Value Definitions
-----------------------

..  module:: softioc.alarm
    :synopsis: Constant definitions for EPICS severity and alarm values

The following values can be passed to IN record :meth:`set` and
:meth:`set_alarm` methods.

..  attribute::
        NO_ALARM = 0
        MINOR_ALARM = 1
        MAJOR_ALARM = 2
        INVALID_ALARM = 3

    These are severity values.  The default severity is :attr:`NO_ALARM`.

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


Automatic PV logging
--------------------

..  module:: softioc.pvlog
    :synopsis: Enables logging of CA puts to PVs

Once this module has been imported all channel access writes to any PV published
by this IOC will be logged by writing a suitable message to stdout.  There is
currently no control or customisation of this feature.
