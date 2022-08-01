import asyncio
import inspect
import logging
import threading
import atexit

class AsyncioDispatcher:
    def __init__(self, loop=None):
        """A dispatcher for `asyncio` based IOCs, suitable to be passed to
        `softioc.iocInit`. Means that `on_update` callback functions can be
        async.

        If a ``loop`` is provided it must already be running. Otherwise a new
        Event Loop will be created and run in a dedicated thread.
        """
        if loop is None:
            # Make one and run it in a background thread
            self.loop = asyncio.new_event_loop()
            worker = threading.Thread(target=self.loop.run_forever)
            # Explicitly manage worker thread as part of interpreter shutdown.
            # Otherwise threading module will deadlock trying to join()
            # before our atexit hook runs, while the loop is still running.
            worker.daemon = True

            @atexit.register
            def aioJoin(worker=worker, loop=self.loop):
                loop.call_soon_threadsafe(loop.stop)
                worker.join()
            worker.start()
        elif not loop.is_running():
            raise ValueError("Provided asyncio event loop is not running")
        else:
            self.loop = loop

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
