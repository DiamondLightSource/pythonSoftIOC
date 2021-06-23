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
    from softioc import builder

    # The PVs we want to average and their initial values
    PVs = [f"DEVICE{i}:CURRENT" for i in range(100)]
    values = np.array(caget(PVs))

    # The PV we want to serve
    avg = builder.aOut("AVERAGE:CURRENT", np.mean(values))

    # Make a monitor on the PVs to keep the value up to date
    def update_avg(value: float, index: int):
        values[index] = value
        avg.set(np.mean(values))

    camonitor(PVs, update_avg)

ADD THE CONCENTRATOR USE CASE HERE

Dynamically created PVs
-----------------------

Other use cases will do something like:

.. code-block::

    connect to device
    make PVs

ADD THE PANDA USE CASE HERE

Existing Python Support
-----------------------

It may be that you have specific device support written in Python that you wish
to expose as PVs.

NEED A GOOD EXAMPLE HERE

