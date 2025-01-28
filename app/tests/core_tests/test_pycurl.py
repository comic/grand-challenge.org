def test_import_pycurl():
    # pycurl is used by celery[sqs] and requires
    # an environment variable to be correctly set
    # at install time, see #3252
    import pycurl

    assert pycurl.version == ""
    assert pycurl
