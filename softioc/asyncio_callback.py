import asyncio
import inspect
import threading


class AsyncioCallback(threading.Thread):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()

    def run(self):
        self.loop.run_forever()

    def __call__(self, func, *args):
        async def async_wrapper():
            ret = func(*args)
            if inspect.isawaitable(ret):
                await ret
        asyncio.run_coroutine_threadsafe(async_wrapper(), self.loop)
