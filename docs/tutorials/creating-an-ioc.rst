Creating an IOC
===============

Introduction
------------

Once the module has been installed (see `installation`) we can create a 
simple EPICS Input/Output Controller (IOC). 

An EPICS IOC created with the help of ``pythonIoc`` and `softioc` is
referred to as a "Python soft IOC".  The code below illustrates a simple IOC
with two Process Variables (PVs):

.. literalinclude:: ../examples/example_cothread_ioc.py

Each section is explained in detail below:

.. literalinclude:: ../examples/example_cothread_ioc.py
    :start-after: # Import
    :end-before: # Set

The `softioc` library is part of ``pythonIoc``. The two submodules 
`softioc.softioc` and `softioc.builder` provide the basic 
functionality for Python soft IOCs and are the ones that are normally used.

`cothread` is one of the two possible libraries the IOC can use for
asynchronous operations. 
(see `../how-to/use-asyncio-in-an-ioc` for the alternative)



.. literalinclude:: ../examples/example_cothread_ioc.py
    :start-after: # Create 
    :end-before: # Boilerplate

PVs are normally created dynamically using `softioc.builder`.  All PV
creation must be done before initialising the IOC. We define a lambda function for 
`on_update` on ``ao`` such that whenever we set ``ao``, ``ai`` will be set to the 
same value. The ``always_update`` flag ensures that the ``on_update`` function is always 
triggered, which is not the default behaviour if the updated value is the same as the
current value.


.. literalinclude:: ../examples/example_cothread_ioc.py
    :start-after: # Boilerplate 
    :end-before: # Start


Initializing the IOC is simply a matter of calling two functions:
:func:`~softioc.builder.LoadDatabase` and :func:`~softioc.softioc.iocInit`,
which must be called in this order.  After calling
:func:`~softioc.builder.LoadDatabase` it is no longer possible to create PVs.

.. literalinclude:: ../examples/example_cothread_ioc.py
    :start-after: # Start 
    :end-before: # Finally

We define a long-running operation that will increment the value of ``ai`` once per
second. This is run as a background thread by `cothread`. 

.. literalinclude:: ../examples/example_cothread_ioc.py
    :start-after: # Finally 

Finally the application must refrain from exiting until the IOC is no longer
needed.  The :func:`~softioc.softioc.interactive_ioc` runs a Python
interpreter shell with a number of useful EPICS functions in scope, and
passing ``globals()`` through can allow interactive interaction with the
internals of the IOC while it's running.  The alternative is to call something
like :func:`cothread.WaitForQuit` or some other `cothread` blocking
action.

In this interpreter there is immediate access to methods defined in the 
`softioc.softioc` module. For example the :func:`~softioc.softioc.dbgf` function
can be run to observe the increasing value of ``AI``::

    >>> dbgf("MY-DEVICE-PREFIX:AI")
    DBF_DOUBLE:         36
    >>> dbgf("MY-DEVICE-PREFIX:AI")
    DBF_DOUBLE:         37

And the :func:`~softioc.softioc.dbpf` method allows data to be set and to observe
the functionality of the lambda passed to ``on_update`` . We set the value on ``AO`` 
and read the value on ``AI`` (exact values will vary based on time taken)::

    >>> dbgf("MY-DEVICE-PREFIX:AI")
    DBF_DOUBLE:         15
    >>> dbpf("MY-DEVICE-PREFIX:AO","999")
    DBF_DOUBLE:         999       
    >>> dbgf("MY-DEVICE-PREFIX:AI")
    DBF_DOUBLE:         1010   


Creating PVs
------------

See the documentation of `softioc.builder` for details, but an overview is
provided here.

PVs are created internally and dynamically using functionality provided by
`epicsdbbuilder`, which in this context simply provides mechanisms for
creating ``.db`` files, but `softioc.builder` also binds each created PV to
a special ``Python`` device -- this allows PV processing to be hooked into
Python support.

PV creation must be done in two stages: first the device name must be set by
calling :func:`~softioc.builder.SetDeviceName`.  After this PVs can be created
by calling any of the following PV creation functions:

    :func:`~softioc.builder.aIn`, :func:`~softioc.builder.aOut`,
    :func:`~softioc.builder.boolIn`, :func:`~softioc.builder.boolOut`,
    :func:`~softioc.builder.longIn`, :func:`~softioc.builder.longOut`,
    :func:`~softioc.builder.stringIn`, :func:`~softioc.builder.stringOut`,
    :func:`~softioc.builder.mbbIn`, :func:`~softioc.builder.mbbOut`,
    :func:`~softioc.builder.Waveform`, :func:`~softioc.builder.WaveformOut`.

These functions create, respectively, ``Python`` device bound records of the
following types:

     ``ai``, ``ao``, ``bi``, ``bo``, ``longin``, ``longout``, ``mbbi``,
     ``mbbo``, ``stringin``, ``stringout``, ``waveform``

Occasionally it may be desirable to create a soft record without ``Python``
device support, particularly if any other record type is required.  This can be done using the corresponding record creation
functions provided as methods of :attr:`softioc.builder.records`.  For example, if a ``calc``
record is required then this can be created by calling
``softioc.builder.records.calc``.

For all records created by these methods both
:meth:`~softioc.device.ProcessDeviceSupportIn.get` and
:meth:`~softioc.device.ProcessDeviceSupportIn.set` methods are available for
reading and writing the current value of the record.  For IN records calling
:meth:`~softioc.device.ProcessDeviceSupportIn.set` will trigger a record update
(all IN records are by default created with ``SCAN='I/O Intr'``).
