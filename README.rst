..  default-role:: literal

Using `pythonSoftIoc`
=====================

Probably the best way to use `pythonSoftIoc` is to start by copying fragments
of a simple example such as `CS-DI-IOC-02`.  This consists of the following
elements:

1. A startup shell script `start-ioc` which launches the soft IOC using a
production build of `pythonSoftIoc`.  This script typically looks like this::

    #!/bin/sh

    PYIOC_VERSION=2-9

    PYIOC=/dls_sw/prod/R3.14.12.3/support/pythonSoftIoc/$PYIOC_VERSION/pythonIoc

    cd "$(dirname "$0")"
    exec $PYIOC start_ioc.py "$@"

2. The startup Python script.  This establishes the essential component
versions (apart from the `pythonSoftIoc` version), performs the appropriate
initialisation and starts the IOC running.  The following template is a useful
starting point::

    from pkg_resources import require
    require('cothread==2.12')
    require('epicsdbbuilder==1.0')

    # Import the basic framework components.
    from softioc import softioc, builder
    import cothread

    # Import any modules required to run the IOC
    import ...

    # Boilerplate get the IOC started
    builder.LoadDatabase()
    softioc.iocInit()

    # Start processes required to be run after iocInit
    ...

    # Finally leave the IOC running with an interactive shell.
    interactive_ioc(globals())
