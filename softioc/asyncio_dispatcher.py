import asyncio
import inspect
import threading


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
            threading.Thread(target=self.loop.run_forever).start()

    def __call__(self, func, *args):
        async def async_wrapper():
            ret = func(*args)
            if inspect.isawaitable(ret):
                await ret
        asyncio.run_coroutine_threadsafe(async_wrapper(), self.loop)
