pythonIoc
=========

|code_ci| |docs_ci| |coverage| |pypi_version| |license|


This module allows an EPICS IOC with Python Device Support to be run from within
the Python interpreter. Records can be programmatically created and arbitrary
Python code run to update them and respond to caputs. It supports cothread and
asyncio for concurrency. PVs are served over Channel Access and PVAccess.

============== ==============================================================
PyPI           ``pip install softioc``
Source code    https://github.com/dls-controls/pythonIoc
Documentation  https://dls-controls.github.io/pythonIoc
============== ==============================================================

A simple example of the use of this library:

.. code:: python

    # Import the basic framework components.
    from softioc import softioc, builder
    import cothread

    # Set the record prefix
    builder.SetDeviceName("MY-DEVICE-PREFIX")

    # Create some records
    ai = builder.aIn('AI', initial_value=5)
    ao = builder.aOut('AO', initial_value=12.45, on_update=lambda v: ai.set(v))

    # Boilerplate get the IOC started
    builder.LoadDatabase()
    softioc.iocInit()

    # Start processes required to be run after iocInit
    def update():
        while True:
            ai.set(ai.get() + 1)
            cothread.Sleep(1)


    cothread.Spawn(update)

    # Finally leave the IOC running with an interactive shell.
    softioc.interactive_ioc(globals())

.. |code_ci| image:: https://github.com/dls-controls/pythonIoc/workflows/Code%20CI/badge.svg?branch=master
    :target: https://github.com/dls-controls/pythonIoc/actions?query=workflow%3A%22Code+CI%22
    :alt: Code CI

.. |docs_ci| image:: https://github.com/dls-controls/pythonIoc/workflows/Docs%20CI/badge.svg?branch=master
    :target: https://github.com/dls-controls/pythonIoc/actions?query=workflow%3A%22Docs+CI%22
    :alt: Docs CI

.. |coverage| image:: https://codecov.io/gh/dls-controls/pythonIoc/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/dls-controls/pythonIoc
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/softioc.svg
    :target: https://pypi.org/project/softioc
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst

See https://dls-controls.github.io/pythonIoc for more detailed documentation.
