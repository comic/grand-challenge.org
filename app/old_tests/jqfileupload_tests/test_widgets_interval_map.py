import pytest

from grandchallenge.jqfileupload.widgets.utils import IntervalMap


def test_interval_map_indexing_and_length():
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
    im.append_interval(1 * 10 ** 32, o)
    # Ans aldo check that no value-copy issues are ocurring
    assert im[1 * 10 ** 32] is o
    assert im.len == 1 * 10 ** 32 + 20
    with pytest.raises(IndexError):
        im[1 * 10 ** 32 + 20]


def test_interval_map_get_offset():
    im = IntervalMap()
    im.append_interval(10, "a")
    im.append_interval(5, "b")
    im.append_interval(3, "c")
    assert im.get_offset(0) == 0
    assert im.get_offset(4) == 0
    assert im.get_offset(9) == 0
    assert im.get_offset(10) == 10
    assert im.get_offset(14) == 10
    assert im.get_offset(15) == 15
    assert im.get_offset(16) == 15
    with pytest.raises(IndexError):
        im.get_offset(18)
    with pytest.raises(IndexError):
        im.get_offset(-1)
    with pytest.raises(TypeError):
        im.get_offset(-1.0)


def test_invalid_types():
    im = IntervalMap()
    im.append_interval(10, "a")
    im.append_interval(5, "b")
    im.append_interval(3, "c")
    with pytest.raises(TypeError):
        im["wrong index"]
    with pytest.raises(IndexError):
        im[-1]
    with pytest.raises(IndexError):
        im[1000000]
    with pytest.raises(TypeError):
        im.get_offset("wrong index")
    with pytest.raises(IndexError):
        im.get_offset(-1)
    with pytest.raises(IndexError):
        im.get_offset(1000000)
