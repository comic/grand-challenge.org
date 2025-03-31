# pyvips should be imported before pycurl to reproduce error
import pyvips


def test_import_pycurl():
    import pycurl

    assert pyvips
    assert pycurl
