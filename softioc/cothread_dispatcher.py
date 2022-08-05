
class CothreadDispatcher:
    def __init__(self, dispatcher = None):
        """A dispatcher for `cothread` based IOCs, suitable to be passed to
        `softioc.iocInit`.  By default scheduled tasks are run on a dedicated
        cothread callback thread, but an alternative dispatcher can optionally
        be specified here.  Realistically the only sensible alternative is to
        pass `cothread.Spawn`, which would create a separate cothread for each
        dispatched callback.
        """

        if dispatcher is None:
            # Import here to ensure we don't instantiate any of cothread's
            # global state unless we have to
            import cothread
            # Create our own cothread callback queue so that our callbacks
            # processing doesn't interfere with other callback processing.
            self.__dispatcher = cothread.cothread._Callback()
        else:
            self.__dispatcher = dispatcher

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
