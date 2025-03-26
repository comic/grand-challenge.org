import time
from datetime import timedelta

from grandchallenge.core.db.postgres_iam.base import thread_local_cache


def test_caching_basic():
    call_count = 0

    @thread_local_cache(ttl=timedelta(seconds=1))
    def test_func(x):
        nonlocal call_count
        call_count += 1
        return call_count

    assert test_func(5) == 1

    assert test_func(5) == 1
    assert call_count == 1


def test_cache_expiration():
    call_count = 0

    @thread_local_cache(ttl=timedelta(seconds=0.5))
    def test_func(x):
        nonlocal call_count
        call_count += 1
        return call_count

    assert test_func(5) == 1

    assert test_func(5) == 1

    time.sleep(0.6)

    assert test_func(5) == 2
    assert call_count == 2


def test_different_arguments():
    call_count = 0

    @thread_local_cache(ttl=timedelta(seconds=1))
    def test_func(x):
        nonlocal call_count
        call_count += 1
        return call_count

    assert test_func(5) == 1
    assert test_func(6) == 2
    assert call_count == 2


def test_multiple_calls_different_args():
    call_count = 0

    @thread_local_cache(ttl=timedelta(seconds=1))
    def test_func(x):
        nonlocal call_count
        call_count += 1
        return call_count

    assert test_func(5) == 1
    assert test_func(6) == 2
    assert test_func(5) == 1
    assert test_func(6) == 2
    assert call_count == 2


def test_keyword_arguments():
    call_count = 0

    @thread_local_cache(ttl=timedelta(seconds=1))
    def test_func(x=None):
        nonlocal call_count
        call_count += 1
        return call_count

    assert test_func(x=5) == 1
    assert test_func(x=5) == 1
    assert test_func(x=6) == 2
    assert call_count == 2
