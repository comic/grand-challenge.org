from grandchallenge.codebuild.models import Build


def test_clean_build_log():
    b = Build()
    b.build_log = "foo\n[Container] bar\nbaz\n"
    assert b.redacted_build_log == "foo\nbaz"
