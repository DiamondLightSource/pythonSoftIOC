Read data from an IOC
======================

This guide explains how to read data from an IOC in a separate Python program.

To start, run the `cothread` IOC from `../tutorials/creating-an-ioc` or the
`asyncio` IOC from `use-asyncio-in-an-ioc` and leave it running at the
interactive shell.

Using Channel Access
--------------------

.. note::
    Please ensure your firewall allows both TCP and UDP traffic on ports 5064 and 5065.
    These are used by EPICS for channel access to the PVs.

We will read data from the IOC using this script:

.. literalinclude:: ../examples/example_read_from_ioc_ca.py

You can run this as::

    python -i example_read_from_ioc_ca.py

From the interactive command line you can now use the ``caget`` and ``caput`` functions to operate on
the PVs exposed in the IOC. Another interesting command to try is::

    camonitor("MY-DEVICE-PREFIX:AI", print)

You should observe the value of ``AI`` being printed out, once per second, every time the PV value
updates.

Using PVAccess
--------------

.. note::
    Please ensure your firewall allows both TCP and UDP traffic on ports 5075 and 5076.
    These are used by EPICS for PVAccess to the PVs.

We will read data from the IOC using this script:

.. literalinclude:: ../examples/example_read_from_ioc_pva.py

You can run this as::

    python -i example_read_from_ioc_pva.py

From the interactive command line you can now use the ``ctx.get`` and ``ctx.put`` functions to operate on
the PVs exposed in the IOC. Another interesting command to try is::

    ctx.monitor("MY-DEVICE-PREFIX:AI", print)

You should observe the value and timestamp of ``AI`` being printed out, once per second, every time the PV value
updates.
