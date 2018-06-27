import contextlib
import uuid


@contextlib.contextmanager
def replace_var(module, value_name, substitute):
    old_value = getattr(module, value_name)
    try:
        setattr(module, value_name, substitute)
        yield
    finally:
        setattr(module, value_name, old_value)



class CeleryTaskCollectorTask:
    """
    Celery mock task used by CeleryTaskCollector to mimic celery.
    """
    def __init__(self, args=(), kwargs={}, countdown=None, eta=None, expires=None):
        self.__uuid = uuid.uuid4()
        self.args = args
        self.kwargs = kwargs

        self.countdown = countdown
        self.eta = eta
        self.expires = expires

    @property
    def id(self):
        return self.__uuid


class CeleryTaskCollector:
    """
    This class provides a dummy celery interface that can be used to
    replace celery shared_task functions. Calls to call_async are collected
    and can later be iterated over using the iteration function of this
    queue.

    Parameters
    ----------
    fun:
        The function, specifically, a celery shared_task that should be
        overridden.
    """
    def __init__(self, fun):
        self.__fun = fun
        self.__calls = []

    def __call__(self, *args, **kwargs):
        """
        Support of direct calls
        """
        return self.__fun(*args, **kwargs)

    def apply_async(self, args=(), kwargs={}, countdown=None, eta=None, expires=None):
        """
        Emulation of apply_async of a shared_job in celery.

        Parameters
        ----------
        args
        kwargs
        countdown
        eta
        expires

        Returns
        -------

        """
        task = CeleryTaskCollectorTask(
            args,
            kwargs,
            countdown=countdown,
            eta=eta,
            expires=expires)
        self.__calls.append(task)
        return task

    def execute_calls(self):
        """
        Consumes all queued tasks and executes them on the main thread.
        """
        while self.__calls:
            call = self.__calls.pop()
            self.__fun(*call.args, **call.kwargs)
