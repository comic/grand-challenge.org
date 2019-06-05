import pytest


def test_factory(factory):
    try:
        factory()
    except Exception as e:
        pytest.fail(
            f"Failed factory initialization for {str(factory)} with exception: {e}"
        )
