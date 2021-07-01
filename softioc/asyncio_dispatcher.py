import asyncio
import inspect
import threading


class AsyncioDispatcher(threading.Thread):
    """A dispatcher for `asyncio` based IOCs. Means that `on_update` callback
    functions can be async. Will run an Event Loop in a thread when
    created.
    """
    def __init__(self):
        """Create an AsyncioDispatcher suitable to be used by
        `softioc.iocInit`."""
        # Docstring specified to suppress threading.Thread's docstring, which
        # would otherwise be inherited by this method and be misleading.
        super().__init__()
        #: `asyncio` event loop that the callbacks will run under.
        self.loop = asyncio.new_event_loop()
        self.start()

    def run(self):
        self.loop.run_forever()

    def __call__(self, func, *args):
        async def async_wrapper():
            ret = func(*args)
            if inspect.isawaitable(ret):
                await ret
        asyncio.run_coroutine_threadsafe(async_wrapper(), self.loop)
