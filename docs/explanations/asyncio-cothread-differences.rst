What are the differences between `asyncio` and `cothread`?
==========================================================

There are two concurrency frameworks that pythonSoftIOC supports, `asyncio` and
`cothread`. This page details the differences between them and reasons why you
should use one over the other

.. seealso::

    `../how-to/use-asyncio-in-an-ioc` for an example of how to use asyncio and
    pythonSoftIOC


The Similarities
----------------

Both frameworks are asynchronous concurrency frameworks, which means that they
run in a single OS thread, and use lightweight coroutines/cothreads for
concurrency. These are more deterministic and use less resources than OS
threads, which makes them well suited to applications like pythonSoftIOC where
many records may be processing concurrently. The biggest advantage is that only
one coroutine runs at any one time. A coroutine will run until it yields control
to another coroutine. This means that changes to shared state can only occur
when it has yielded control, which reduces the need for mutexes that would be
needed in threaded code.


The Differences
---------------

The main difference between the libraries is how a coroutine yields control.

- `asyncio` uses an ``async def`` which will yield control when they ``await``.
  Only an ``async def`` can ``await`` another ``async def``, so functions that
  yield control are explicitly marked as such by the presence of the ``async``
  keyword.
- `cothread` has the :func:`~cothread.Yield` function which can be used in any
  ordinary ``def``. The yield is implicit as you need to read the
  documentation/source code to find out if a function will yield control

For example, an `on_update` function written using cothread might be::

    import cothread
    from softioc import builder

    def something_that_yields_control(value):
        cothread.Sleep(0.1)

    def update_ao(value):
        something_that_yields_control(value)
        print(value)

    builder.aOut('AO', on_update=update_ao)

While the same example written using asyncio is::

    import asyncio
    from softioc import builder

    async def something_that_yields_control(value):
        await asyncion.sleep(0.1)

    async def update_ao(value):
        await something_that_yields_control(value)
        print(value)

    builder.aOut('AO', on_update=update_ao)

Note that because ``something_that_yields_control()`` is an ``async def``,
``update_ao()`` needs to be to.

.. seealso::

    https://glyph.twistedmatrix.com/2014/02/unyielding.html for a discussion on
    explicit vs implicit yield


Which to use
------------

There are some questions to ask to help you choose which one to use:

- If you run python2.7 then you need to use `cothread` as `asyncio` is python3
  only
- If you run on Windows then you need `asyncio` as `cothread` doesn't work on
  Windows
- If you need to integrate with a library that uses `asyncio` like one from
  aio-libs_ then use `asyncio`
- If you need to turn a script using `cothread.catools` into an IOC then use
  `cothread`

In general, avoid mixing concurrency frameworks if you can. While it is possible
to mix `asyncio` and `cothread`, it's messy and tricky to get right. Better to
keep to one if possible.

.. _aio-libs: https://github.com/aio-libs



