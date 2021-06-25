PythonIOC
=========

|code_ci| |docs_ci| |coverage| |pypi_version| |license|


This module allows an EPICS IOC with Python Device Support to be run from within
the Python interpreter. Records can be programmatically created and arbitrary
Python code run to update them and respond to caputs. It supports cothread and
asyncio for concurrency.

============== ==============================================================
PyPI           ``pip install softioc``
Source code    https://github.com/dls-controls/pythonIoc
Documentation  https://dls-controls.github.io/pythonIoc
============== ==============================================================

A simple example of the use of this library is the following:

.. literalinclude:: examples/example_cothread_ioc.py    


.. |code_ci| image:: https://github.com/dls-controls/pythonIoc/workflows/Code%20CI/badge.svg?branch=master
    :target: https://github.com/dls-controls/pythonIoc/actions?query=workflow%3A%22Code+CI%22
    :alt: Code CI

.. |docs_ci| image:: https://github.com/dls-controls/pythonIoc/workflows/Docs%20CI/badge.svg?branch=master
    :target: https://github.com/dls-controls/pythonIoc/actions?query=workflow%3A%22Docs+CI%22
    :alt: Docs CI

.. |coverage| image:: https://codecov.io/gh/dls-controls/pythonIoc/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/dls-controls/pythonIoc
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/pythonIoc.svg
    :target: https://pypi.org/project/pythonIoc
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst

See https://dls-controls.github.io/pythonIoc for more detailed documentation.