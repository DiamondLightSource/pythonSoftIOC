Create a Publishable IOC
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
    only ``pkg_resources.require`` statements, simple code to start the body
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