from django.db.models.query import QuerySet


def filter_queryset_field(field, value, model=None, queryset=None) -> QuerySet:
    if queryset is None and model is None:
        raise ValueError("Unable to initialize or utilize queryset.")

    if model is not None:
        queryset = model.objects.all()

    if value is not None:
        filter_argument = {field: value}
        queryset = queryset.filter(**filter_argument)

    return queryset


def filter_queryset_fields(field_filters, model=None, queryset=None) -> QuerySet:
    if queryset is None and model is None:
        raise ValueError("Unable to initialize or utilize queryset.")

    if model is not None:
        queryset = model.objects.all()

    for field, value in field_filters.items():
        if value is not None:
            queryset = queryset.filter(**{field: value})

    return queryset
