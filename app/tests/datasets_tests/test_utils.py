from grandchallenge.datasets.utils import infer_type, type_values


def test_infer_type():
    assert infer_type("10.0") == 10.0
    assert isinstance(infer_type("10.0"), float)
    assert infer_type("10") == 10
    assert isinstance(infer_type("10"), int)
    assert infer_type("10.5") == 10.5
    assert infer_type("foo") == "foo"


def test_type_values():
    input = {"float": "10.0", "int": "10", "5": "5", "foo": "bar"}

    o = type_values(input)

    assert o["float"] == float(input["float"])
    assert o["int"] == int(input["int"])
    assert o["5"] == int(input["5"])
    assert o["foo"] == input["foo"]
