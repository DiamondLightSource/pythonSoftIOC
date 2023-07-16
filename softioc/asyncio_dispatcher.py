import asyncio
import inspect
import logging
import threading
import atexit

class AsyncioDispatcher:
    def __init__(self, loop=None, debug=False):
        """A dispatcher for `asyncio` based IOCs, suitable to be passed to
        `softioc.iocInit`. Means that `on_update` callback functions can be
        async.

        If a ``loop`` is provided it must already be running. Otherwise a new
        Event Loop will be created and run in a dedicated thread.
        ``debug`` is passed through to ``asyncio.run()``.

        For a clean exit, call ``softioc.interactive_ioc(..., call_exit=False)``
        """
        if loop is None:
            # will wait until worker is executing the new loop
            started = threading.Event()
            # Make one and run it in a background thread
            self.__worker = threading.Thread(target=asyncio.run,
                                             args=(self.__inloop(started),),
                                             kwargs={'debug': debug})
            # Explicitly manage worker thread as part of interpreter shutdown.
            # Otherwise threading module will deadlock trying to join()
            # before our atexit hook runs, while the loop is still running.
            self.__worker.daemon = True

            self.__worker.start()
            started.wait()

            self.__atexit = atexit.register(self.__shutdown)

            assert self.loop is not None and self.loop.is_running()

        elif not loop.is_running():
            raise ValueError("Provided asyncio event loop is not running")
        else:
            self.loop = loop

    def close(self):
        if self.__atexit is not None:
            atexit.unregister(self.__atexit)
            self.__atexit = None

        self.__shutdown()

    async def __inloop(self, started):
        self.loop = asyncio.get_running_loop()
        self.__interrupt = asyncio.Event()
        started.set()
        del started
        await self.__interrupt.wait()

    def __shutdown(self):
        if self.__worker is not None:
            self.loop.call_soon_threadsafe(self.__interrupt.set)
            self.__worker.join()
            self.__worker = None

    def __call__(
            self,
            func,
            func_args=(),
            completion = None,
            completion_args=()):
        async def async_wrapper():
            try:
                ret = func(*func_args)
                if inspect.isawaitable(ret):
                    await ret
                if completion:
                    completion(*completion_args)
            except Exception:
                logging.exception("Exception when running dispatched callback")
        asyncio.run_coroutine_threadsafe(async_wrapper(), self.loop)

    def __enter__(self):
        return self

    def __exit__(self, A, B, C):
        self.close()
