import pytest
from django.db import models
from rest_framework.exceptions import ErrorDetail


def check_if_field_in_serializer(fields, serializer_fields):
    for field in fields:
        if field not in serializer_fields:
            pytest.fail(f"Field {field!r} missing in serializer")
    for field in serializer_fields:
        if field not in fields:
            pytest.fail(f"Serializer field {field!r} missing in test")


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


def check_if_valid_unique(model_or_factory, serializer, request=None):
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

    if request is not None:
        context = {"request": request}
    else:
        context = {}

    model_serializer = serializer(data=serializer(model, context=context).data)
    valid = model_serializer.is_valid()
    if not valid:
        filtered_errors = exclude_unique_errors(model_serializer.errors)
        if not filtered_errors:
            # if the unique error is the only error in model_serializer.errors, return True
            valid = True
    return valid


def do_test_serializer_valid(serializer_data, request=None):
    if not serializer_data.get("no_valid_check"):
        if serializer_data["unique"]:
            assert check_if_valid_unique(
                serializer_data["factory"],
                serializer_data["serializer"],
                request,
            )
        else:
            assert check_if_valid(
                serializer_data["factory"], serializer_data["serializer"]
            )


def do_test_serializer_fields(serializer_data, request=None):
    if not serializer_data.get("no_contains_check"):

        if request is not None:
            context = {"request": request}
        else:
            context = {}

        check_if_field_in_serializer(
            serializer_data["fields"],
            serializer_data["serializer"](
                serializer_data["factory"](), context=context
            ).data.keys(),
        )


def exclude_unique_errors(errors_object):
    """Helper function that recursively excludes all unique errors"""
    filtered_error_object = {}
    for field_key, errors_list in errors_object.items():
        filtered_errors_list = []
        errors_list = (
            errors_list if isinstance(errors_list, list) else [errors_list]
        )
        for error in errors_list:
            if isinstance(error, dict):
                # nested object
                nested_errors = exclude_unique_errors(error)
                if nested_errors:
                    filtered_errors_list.append(nested_errors)
            elif isinstance(error, ErrorDetail):
                if error.code != "unique":
                    filtered_errors_list.append(error)
            else:
                raise TypeError(
                    f"Expected dict or ErrorDetail for {error} got {type(error)}"
                )
        if len(filtered_errors_list) > 0:
            filtered_error_object[field_key] = filtered_errors_list
    return filtered_error_object
