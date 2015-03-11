.. _pythonsoftioc:

Python Soft IOC
===============

The ``pythonIoc`` command is a tool for creating and running an EPICS IOC
entirely within Python.


Introduction
------------

The Python Soft IOC consists of two components: a command ``pythonIoc`` and an
associated library :mod:`softioc`.  The ``pythonIoc`` command consists of a bare
EPICS IOC linked together with the DLS Python interpreter and configured so that
startup arguments are interpreted by the Python interpreter -- this means that
when ``pythonIoc`` is run it behaves the same as running ``dls-python``.

Scripts run from within ``pythonIoc`` differ from standard Python scripts in one
detail: they have the ability to create and publish PVs through the
:mod:`softioc` library.  Typically both :mod:`cothread` and
:mod:`epicsdbbuilder` will be recruited to help: :mod:`cothread` is used for
dispatching OUT record processing callback methods, :mod:`epicsdbbuilder` is
used for constructing records during IOC initialisation.

An EPICS IOC created with the help of ``pythonIoc`` and :mod:`softioc` is
referred to as a "Python soft IOC".  The code below illustrates a simple IOC
with one PV::

    # DLS requires
    from pkg_resources import require
    require('cothread==2.12')
    require('epicsdbbuilder==1.0')

    # Import basic softioc framework
    from softioc import softioc, builder

    # Create PVs
    builder.SetDeviceName('TS-TEST-TEST-01')
    builder.stringIn('TEST', initial_value = 'This is a test')

    # Run the IOC.  This is boilerplate, and must always be done in this order,
    # and must always be done after creating all PVs.
    builder.LoadDatabase()
    softioc.iocInit()

    softioc.interactive_ioc(globals())

This example script illustrates the following points.

- The use of :func:`pkg_resources.require` is standard across all use of the
  ``dls-python`` Python interpreter at Diamond, and in this example we are using
  both :mod:`cothread` and :mod:`epicsdbbuilder`.  Of course, in an officially
  published IOC specific versions must be specified, in this example I'm using
  the most recent versions at the time of writing.

- The :mod:`softioc` library is part of ``pythonIoc`` and is automatically added
  to the path.  The two submodules :mod:`softioc.softioc` and
  :mod:`softioc.builder` provide the basic functionality for Python soft IOCs
  and are the ones that are normally used.

- PVs are normally created dynamically using :mod:`softioc.builder`.  All PV
  creation must be done before initialising the IOC.

- Once PVs have been created then the associated EPICS database can be created
  and loaded into the IOC and then the IOC can be started.

- Finally the application must refrain from exiting until the IOC is no longer
  needed.  The :func:`~softioc.softioc.interactive_ioc` runs a Python
  interpreter shell with a number of useful EPICS functions in scope, and
  passing ``globals()`` through can allow interactive interaction with the
  internals of the IOC while it's running.  The alternative is to call something
  like :func:`cothread.WaitForQuit` or some other :mod:`cothread` blocking
  action.


Creating a Publishable IOC
--------------------------

As the example script above shows, a single Python script can be an IOC.
However, to fit into the DLS framework for publishing IOCs in ``/dls_sw/prod`` a
bit more structure is needed.  I recommend at least four files as shown:

``Makefile``
    This file is necessary in order to run ``dls-release.py``, and needs to have
    both ``install`` and ``clean`` targets, but doesn't need to actually do
    anything.  Thus the following content for this file is enough::

        install:
        clean:

``start-ioc``
    An executable file for starting the IOC needs to be created.  I recommend
    that this consist of the following boilerplate::

        #!/bin/sh

        PYIOC_VER=2-6
        EPICS_VER=3.14.12.3

        PYIOC=/dls_sw/prod/R$EPICS_VER/support/pythonSoftIoc/$PYIOC_VER/pythonIoc

        exec $PYIOC ioc_entry.py "$@"

    Here I have given the startup script for the IOC the name ``ioc_entry.py``.
    This name should be replaced by any appropriate name.

``ioc_entry.py``
    I recommend that the top level Python script used to launch the IOC contain
    only :func:`pkg_resources.require` statements, simple code to start the body
    of the IOC, and it should end with standard code to start the IOC.  The
    following structure can be followed (here I've assumed that the rest of the
    IOC is in a single file called ``ioc_body.py``::

        from pkg_resources import require

        require('cothread==2.12')
        require('epicsdbbuilder==1.0')
        # Any other requires needed by this IOC

        from softioc import softioc

        # Do whatever makes sense to create all the PVs and get ready to go
        import ioc_body
        ioc_body.initialise()

        # Start the IOC -- this is boilerplate
        builder.LoadDatabase()
        softioc.iocInit()

        # If activities need to be started after iocInit, now's the time
        ioc_body.start()

        softioc.interactive_ioc(globals())

    Note that *all* requires *must* occur in this initial startup file.

The rest of the IOC
    Of course, a Python script can be structured into any number of Python
    modules.  In the example above I have illustrated just one such module
    called ``ioc_body.py`` with two entry points.


Creating PVs
------------

See the documentation of :mod:`softioc.builder` for details, but an overview is
provided here.

PVs are created internally and dynamically using functionality provided by
:mod:`epicsdbbuilder`, which in this context simply provides mechanisms for
creating ``.db`` files, but :mod:`softioc.builder` also binds each created PV to
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
functions provided as methods of :attr:`records`.  For example, if a ``calc``
record is required then this can be created by calling
:func:`softioc.builder.records.calc`.

For all records created by these methods both
:meth:`~softioc.device.ProcessDeviceSupportIn.get` and
:meth:`~softioc.device.ProcessDeviceSupportIn.set` methods are available for
reading and writing the current value of the record.  For IN records calling
:meth:`~softioc.device.ProcessDeviceSupportIn.set` will trigger a record update
(all IN records are by default created with ``SCAN='I/O Intr'``).


Initialising the IOC
--------------------

This is simply a matter of calling two functions:
:func:`~softioc.builder.LoadDatabase` and :func:`~softioc.softioc.iocInit`,
which must be called in this order.  After calling
:func:`~softioc.builder.LoadDatabase` it is no longer possible to create PVs.

It is sensible to start any server background activity after the IOC has been
initialised by calling :func:`~softioc.softioc.iocInit`.  After this has been
done (:func:`cothread.Spawn` is recommended for initiating persistent background
activity) the top level script must pause, as as soon as it exits the IOC will
exit.  Calling :func:`~softioc.softioc.interactive_ioc` is recommended for this
as the last statement in the top level script.
