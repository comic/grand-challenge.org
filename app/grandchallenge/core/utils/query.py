from contextlib import contextmanager

from django.db import OperationalError, connection

from grandchallenge.core.exceptions import LockNotAcquiredException


def index(queryset, obj):
    """
    Give the zero-based index of first occurrence of object in queryset.
    Return -1 if not found
    """
    for index, item in enumerate(queryset):
        if item == obj:
            return index

    return -1


def set_seed(seed):
    # Note: this only works for postgres, if we ever switch dbs, this
    # may need changing.
    cursor = connection.cursor()
    cursor.execute(f"SELECT setseed({seed});")
    cursor.close()


@contextmanager
def check_lock_acquired():
    try:
        yield
    except OperationalError as error:
        if "could not obtain lock" in str(error):
            raise LockNotAcquiredException from error
        else:
            raise error
