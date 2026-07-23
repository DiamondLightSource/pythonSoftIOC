Use `softioc.autosave` in an IOC
================================

`../tutorials/creating-an-ioc` shows how to create a pythonSoftIOC.


Example IOC
-----------

.. literalinclude:: ../examples/example_autosave_ioc.py

Records are instantiated as normal and configured for automatic loading and
periodic saving to a backup file with use of the keyword argument ``autosave``.
``autosave`` resolves to a list of strings, which are the names of fields to be
tracked by autosave. By default ``autosave=False``, which disables autosave for that PV.
Setting ``autosave=True`` is equivalent to passing ``["VAL"]``. Note that ``"VAL"`` must be
explicitly passed when tracking other fields, e.g. ``["VAL", "LOPR", "HOPR"]``.
``autosave`` can also accept a single string field name as an argument.

The field values get written into a yaml-formatted file containing key-value pairs.
By default the keys are the same as the full PV name, including any device name specified
in :func:`~softioc.builder.SetDeviceName()`.

Autosave is disabled until :func:`~softioc.autosave.configure()` is called. The first two arguments,
``directory`` and ``name`` are required. Backup files are periodically written into
``directory`` with the name ``<name>.softsav`` every ``save_period`` seconds,
set to 30.0 by default. The directory must exist, and should be configured with the appropriate
read/write permissions for the user running the IOC.

IOC developers should only need to interface with autosave via the :func:`~softioc.autosave.configure()`
method and the ``autosave`` keyword argument. Alternatively,
PVs can be instantiated inside the :class:`~softioc.autosave.Autosave()` context manager, which 
automatically passes the ``autosave`` argument to any PVs created
inside the context manager. If any fields are already specified by the ``autosave`` keyword
argument of a PV's initialisation call the lists of fields to track get combined.
All other module members are intended for internal use only.

In normal operation, loading from a backup is performed once during the
:func:`~softioc.builder.LoadDatabase()` call and periodic saving to the backup file begins when
:func:`~softioc.softioc.iocInit()` is called, provided that any PVs are configured to be saved.
Currently, manual loading from a backup at runtime after ioc initialisation is not supported.
Saving only occurs when any of the saved field values have changed since the last save.
Users are discouraged from manually editing the backup files while the
IOC is running so that the internal state of the autosave thread is consistent with
the backup file.

If autosave is enabled and active, a timestamped copy of the latest existing autosave backup file is created
when the IOC is restarted, e.g. ``<name>.softsav_240717-095004`` (timestamps are in the format yymmdd-HHMMSS).
If you only wish to store one backup of the autosave file at a time, ``timestamped_backups=False``
can be passed to :func:`~softioc.autosave.configure()` when it is called, this will create a backup file
named ``<name>.softsav.bu``. To disable any autosaving, comment out the
:func:`~softioc.autosave.configure()` call or pass it the keyword argument
``enabled=False``.

The resulting backup file after running the example IOC for about 30 seconds is the following:

.. code-block::

    MY-DEVICE-PREFIX:AI.EGU: ''
    MY-DEVICE-PREFIX:AI.PREC: '0'
    MY-DEVICE-PREFIX:AO: 0.0
    MY-DEVICE-PREFIX:AUTOMATIC-AO: 0.0
    MY-DEVICE-PREFIX:AUTOMATIC-AO.EGU: ''
    MY-DEVICE-PREFIX:AUTOMATIC-AO.HOPR: '0'
    MY-DEVICE-PREFIX:AUTOMATIC-AO.LOPR: '0'
    MY-DEVICE-PREFIX:SECONDSRUN: 29
    MY-DEVICE-PREFIX:WAVEFORMIN: [0, 0, 0, 0]


If the IOC is stopped and restarted, the SECONDSRUN record will load its saved
value of 29 from the backup.
All non-VAL fields are stored as strings. Waveform type records holding arrays
are cast into lists before saving.

This example IOC uses cothread, but autosave works identically when using
an asyncio dispatcher.
