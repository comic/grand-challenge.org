import pytest
from django.db import models


def check_if_field_in_serializer(fields, serializer_fields):
    for field in fields:
        if field not in serializer_fields:
            pytest.fail(f"Field '{field}' missing in serializer")
    for field in serializer_fields:
        if field not in fields:
            pytest.fail(f"Serializer field '{field}' missing in test")


def check_if_valid(model_or_factory, serializer):
    """
    Function that checks if a model is valid according to the passed serializer.
    The function saves the model and then checks validness through the serializer
    This means that if the model contains unique constraints it will be invalid.
    Use the function below for models with uniqueness constraints
    :param model_or_factory: model or factory to check
    :param serializer: corresponding serializer
    :return: True/False
    """
    if isinstance(model_or_factory, models.Model):
        # model
        model = model_or_factory
    else:
        # factory, create model
        model = model_or_factory()
    model_serializer = serializer(data=serializer(model).data)
    valid = model_serializer.is_valid()
    return valid


def check_if_valid_unique(model_or_factory, serializer):
    """
    Function that checks if a model is valid according to the passed serializer.
    Ignores validation errors for uniqueness
    :param model_or_factory: model or factory to check
    :param serializer: corresponding serializer
    :return: True/False
    """
    if isinstance(model_or_factory, models.Model):
        # model
        model = model_or_factory
    else:
        # factory, create model
        model = model_or_factory()
    model_serializer = serializer(data=serializer(model).data)
    valid = model_serializer.is_valid()
    if not valid and "non_field_errors" in model_serializer.errors:
        for error in model_serializer.errors["non_field_errors"]:
            if (
                error.code == "unique"
                and len(model_serializer.errors["non_field_errors"]) == 1
                and len(model_serializer.errors) == 1
            ):
                # if the unique error is the only error in model_serializer.errors, return True
                valid = True
    return valid


def do_test_serializer_valid(serializer_data):
    if not serializer_data.get("no_valid_check"):
        if serializer_data["unique"]:
            assert check_if_valid_unique(
                serializer_data["factory"], serializer_data["serializer"]
            )
        else:
            assert check_if_valid(
                serializer_data["factory"], serializer_data["serializer"]
            )


def do_test_serializer_fields(serializer_data):
    if not serializer_data.get("no_contains_check"):
        check_if_field_in_serializer(
            serializer_data["fields"],
            serializer_data["serializer"](
                serializer_data["factory"]()
            ).data.keys(),
        )
