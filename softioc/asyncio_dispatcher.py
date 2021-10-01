import asyncio
import inspect
import logging
import threading
import atexit

class AsyncioDispatcher:
    def __init__(self, loop=None):
        """A dispatcher for `asyncio` based IOCs, suitable to be passed to
        `softioc.iocInit`. Means that `on_update` callback functions can be
        async. If loop is None, will run an Event Loop in a thread when created.
        """
        #: `asyncio` event loop that the callbacks will run under.
        self.loop = loop
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

    def __call__(self, func, *args):
        async def async_wrapper():
            try:
                ret = func(*args)
                if inspect.isawaitable(ret):
                    await ret
            except Exception:
                logging.exception("Exception when awaiting callback")
        asyncio.run_coroutine_threadsafe(async_wrapper(), self.loop)
