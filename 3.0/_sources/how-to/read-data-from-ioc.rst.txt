Read data from an IOC
======================

This guide explains how to read data from an IOC in a separate Python program. 

.. note:: 
    Please ensure your firewall allows both TCP and UDP traffic on ports 5064 and 5065. 
    These are used by EPICS for channel access to the PVs.


To start, run the `cothread` IOC from `../tutorials/creating-an-ioc` or the 
`asyncio` IOC from `use-asyncio-in-an-ioc` and leave it running at the 
interactive shell.

We will read data from that IOC using this script:

.. literalinclude:: ../examples/example_read_from_ioc.py

.. note::
    You may see warnings regarding the missing "caRepeater" program. This is an EPICS tool
    that is used to track when PVs start and stop. It is not required for this simple example,
    and so the warning can be ignored.

From the interactive command line you can now use the ``caget`` and ``caput`` functions to operate on 
the PVs exposed in the IOC. Another interesting command to try is::

    camonitor("MY-DEVICE-PREFIX:AI", lambda val: print(val))


You should observe the value of ``AI`` being printed out, once per second, every time the PV value
updates. 