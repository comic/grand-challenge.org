import pytest


def batch_test_factories(factories, test_class):
    """
    Helper function to test if factory execution works. Executes pytest.fail if fails
    :param factories: dict of factories with name as key
    :param test_class: name of test class
    :return:
    """
    for name, factory in factories.items():
        test_method = create_test_model_method(name, factory)
        test_method.__name__ = "test_{}_factory".format(name)
        setattr(test_class, test_method.__name__, test_method)


def create_test_model_method(name, factory):
    def test_method(self):
        try:
            factory()
        except:
            pytest.fail("Failed model creation for {}".format(name))
    return test_method
