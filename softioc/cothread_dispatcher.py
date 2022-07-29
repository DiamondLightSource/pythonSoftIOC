
class CothreadDispatcher:
    def __init__(self):
        """A dispatcher for `cothread` based IOCs, suitable to be passed to
        `softioc.iocInit`. """
        # Import here to ensure we don't instantiate any of cothread's global
        # state unless we have to
        import cothread
        # Create our own cothread callback queue so that our callbacks
        # processing doesn't interfere with other callback processing.
        self.__dispatcher = cothread.cothread._Callback()

    def __call__(
            self,
            func,
            func_args=(),
            completion = None,
            completion_args=()):
        def wrapper():
            func(*func_args)
            if completion:
                completion(*completion_args)
        self.__dispatcher(wrapper)
