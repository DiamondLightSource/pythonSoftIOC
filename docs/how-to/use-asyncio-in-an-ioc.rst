Use `asyncio` in an IOC
=======================

There are two libraries available for asynchronous operations in PythonIOC:
`cothread` and `asyncio`. This guide shows how to use the latter in
an IOC.

.. note::
    This page only explains the differences between using `cothread` and `asyncio`.
    For more thorough explanation of the IOC itself see `../tutorials/creating-an-ioc`

.. literalinclude:: ../examples/example_asyncio_ioc.py


The ``dispatcher`` is created and passed to :func:`~softioc.softioc.iocInit`. This is what 
allows the use of `asyncio` functions in this IOC. It contains a new event loop to handle
this.

The ``async update`` function will increment the value of ``ai`` once per second,
sleeping that coroutine between updates.
Note that we run this coroutine in the ``loop`` of the ``dispatcher``, and not in the
main event loop.

This IOC will, like the one in `../tutorials/creating-an-ioc`, leave an interactive 
shell open. The values of the PVs can be queried using the methods defined in the 
`softioc.softioc` module.


Asynchronous Channel Access
---------------------------

PVs can be retrieved externally from a PV in an asynchronous manner by using the :py`aioca` module. 
It provides ``await``-able implementations of ``caget``, ``caput``, etc. See that module for more information.
