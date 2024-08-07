Use `softioc.autosave` in an IOC
=======================

`../tutorials/creating-an-ioc` shows how to create a pythonSoftIOC.


Example IOC
-----------

.. literalinclude:: ../examples/example_autosave_ioc.py

Records are instantiated as normal and configured for automatic loading and
periodic saving to a backup file with the keyword arguments ``autosave`` and ``autosave_fields``.
Records with ``autosave=True`` (``False`` by default) have their
VAL fields backed up. Additional record fields in a list passed to ``autosave_fields`` will be backed
up, note that this applies even when ``autosave`` is ``False``.

The field values get written into a yaml-formatted file containing key-value pairs,
by default the keys are the same as the record name passed as the first argument to the
`builder.<RECORD_TYPE>()` call, excluding the device name specified in the `builder.SetDeviceName()`
call.

Autosave is disabled by default until `autosave.configure()` is called. The first two arguments,
``directory`` and ``name`` are required. Backup files are periodically written into
``directory`` with the name ``<name>.softsav`` every ``save_period`` seconds,
set to 30.0 by default. The directory must exist, and should be configured with the appropriate
read/write permissions for the user running the IOC.

IOC developers should only need to interface with autosave via the `autosave.configure()`
method and the ``autosave`` and ``autosave_fields`` keyword arguments,
all other module members are intended for internal use only.

In normal operation, loading from a backup is performed once during the
`builder.LoadDatabase()` call, periodic saving to the backup file begins when
`softioc.iocInit()` is called, provided that any PVs are configured to be saved.
Saving only occurs when any of the saved field values have changed since the last save.
Users are discouraged from manually editing the backup files while the
IOC is running so that the internal state of the autosave thread is consistent with
the backup file.

If autosave is enabled and active, a timestamped copy of the latest existing autosave backup file is created
when the IOC is restarted, e.g. ``<name>.softsav_240717-095004`` (timestamps are in the format yymmdd-HHMMSS).
If you only wish to store one backup of the autosave file at a time, ``timestamped_backups=False`` can be passed to `autosave.configure()`,
this will create a backup file named ``<name>.softsav.bu``.
To disable any autosaving, comment out the `autosave.configure()` call or pass it the keyword argument
``enabled=False``.

The resulting backup file after running the IOC for a minute is the following:

.. code-block::

    AI.EGU: ''
    AI.PREC: '0'
    AO: 0.0
    MINUTESRUN: 1
    WAVEFORMOUT: [0, 0, 0, 0]

If the IOC is stopped and restarted, the MINUTESRUN record will load its saved
value of 1 from the backup.
All non-VAL fields are stored as strings. Waveform type records holding arrays
are cast into lists before saving.

This example IOC uses cothread, but autosave works identically when using
an asyncio dispatcher.