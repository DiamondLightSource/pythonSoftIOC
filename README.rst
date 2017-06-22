..  default-role:: literal

Building `pythonSoftIoc`
========================

To build `pythonSoftIoc` follow these steps:

1.  Edit the following files:

    `configure/RELEASE`
        Set `EPICS_BASE` to point to your local installation of EPICS.

    `configure/CONFIG_SITE`
        Set `PYTHON` to the executable name of your Python interpreter.

2.  Build `pythonIoc` without documentation by running::

        make BUILD_DOCS=

    At this point you should be able to run `./pythonIoc` which will give you an
    interative Python interpreter.

3.  Now ensure that you have numpy_, cothread_, and epicsdbbuilder_ installed.  These can
    be installed unversioned, or versioned (in which case
    `pkg_resources.require` will need to be used), or just localling built and
    added to your `PYTHONPATH`.

4.  Now check that `pythonIoc` works by running `example/runtest`.  You may need
    to edit `example/version.py` if you're using a versioned install of
    `cothread` and `epicsdbbuilder`.

5.  Finally build the documentation by running::

        make docs

    Again, if your installation of components is versioned you may need to edit
    `docs/conf.py` as appropriate.


Using `pythonSoftIoc`
=====================

Probably the best way to use `pythonSoftIoc` is to start by copying fragments
of a simple example such as `CS-DI-IOC-02`.  This consists of the following
elements:

1.  A startup shell script `start-ioc` which launches the soft IOC using a
    production build of `pythonSoftIoc`.  This script typically looks like
    this::

        #!/bin/sh

        PYIOC=/path/to/pythonSoftIoc/pythonIoc

        cd "$(dirname "$0")"
        exec $PYIOC start_ioc.py "$@"

2.  The startup Python script.  This establishes the essential component
    versions (apart from the `pythonSoftIoc` version), performs the appropriate
    initialisation and starts the IOC running.  The following template is a
    useful starting point::

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

    Note that the use of `require` is specific to DLS, and you may have a
    different way of managing your installations.

..  _numpy: http://www.numpy.org/
..  _cothread: https://github.com/dls-controls/cothread
..  _epicsdbbuilder: https://github.com/Araneidae/epicsdbbuilder
