import pytest

from evaluation.widgets.utils import IntervalMap

def test_interval_map():
    im = IntervalMap()

    im.append_interval(10, 1)
    im.append_interval(10, 2)

    assert ([1] * 10 + [2] * 10) == list(im)
    assert len(im) == 20
    assert im.len == 20

    with pytest.raises(IndexError):
        im[-1]
    with pytest.raises(IndexError):
        im[2000]
    with pytest.raises(TypeError):
        im[0.1]

    # Test if we can handle HUUUGE intervals
    o = object()
    im.append_interval(1 * 10**32, o)

    # Ans aldo check that no value-copy issues are ocurring
    assert im[1 * 10**32] is o
    assert im.len == 1 * 10**32 + 20

    with pytest.raises(IndexError):
        im[1 * 10**32 + 20]
