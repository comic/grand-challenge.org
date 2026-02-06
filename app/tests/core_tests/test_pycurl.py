import pycurl


def test_import_pycurl():
    # This is used by Kombu SQS and sometimes has import errors
    assert pycurl
