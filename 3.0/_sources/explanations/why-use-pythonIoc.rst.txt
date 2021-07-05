Why use pythonIOC?
==================

EPICS IOCs are flexible and modular, why do we need to wrap it in Python? This
page attempts to answer that question and list a few good use-cases for it.

Calculating PVs from other values
---------------------------------

Some use cases require PVs to be calculated from multiple sources. This is
possible in EPICS records with ``calc`` or ``aSub`` records, but pythonIoc
allows you to write this as:

.. code-block::

    import numpy as np
    from cothread.catools import caget, camonitor
    from softioc import builder, softioc

    # The PVs we want to average and their initial values
    PVs = [f"DEVICE{i}:CURRENT" for i in range(100)]
    values = np.array(caget(PVs))

    # The PV we want to serve
    avg = builder.aOut("AVERAGE:CURRENT", np.mean(values))

    # Start the IOC
    builder.LoadDatabase()
    softioc.iocInit()

    # Make a monitor on the PVs to keep the value up to date
    def update_avg(value: float, index: int):
        values[index] = value
        avg.set(np.mean(values))

    camonitor(PVs, update_avg)

    # Leave the IOC running with an interactive shell.
    softioc.interactive_ioc(globals())

Dynamically created PVs
-----------------------

Other use cases will require PVs to be created based on the features of a
device. As EPICS database records are statically created at IOC boot, you
can generate the database with a script, but pythonIoc allows you to write
this as:

.. code-block::

    from my_device_lib import Device
    import cothread
    from softioc import builder, softioc

    # Connect to the device
    device = Device("hostname")
    device.connect()

    # Make a record for each parameter it has
    records = {}
    for param in device.get_params():
        records[param] = builder.aIn(param.name, param.value)

    # Start the IOC
    builder.LoadDatabase()
    softioc.iocInit()

    # Poll the device for changes and update the records
    def update_params():
        while True:
            for param in device.poll_changed_params():
                records[param].set(param.value)

    cothread.Spawn(update_params)

    # Leave the IOC running with an interactive shell.
    softioc.interactive_ioc(globals())

ADD THE PANDA USE CASE HERE

Existing Python Support
-----------------------

It may be that you have specific device support written in Python that you wish
to expose as PVs. This could be either in the form of a device support library
or using a Python library to calculate PV values as above.

ADD THE FURKA/GRIMSEL MONITORING IOC USE CASE HERE
