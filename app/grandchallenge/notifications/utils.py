import collections
from collections import namedtuple

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Code in this file was adapted from https://djangosnippets.org/snippets/2492/
# and https://andrew.hawker.io/writings/2020/11/18/django-activity-stream-prefetch-generic-foreign-key/


def _queryset_foreign_keys(queryset):
    """
    Build mapping of name -> field for GenericForeignKey or
    ForwardManyToOneDescript fields on the queryset.
    """
    fks = {}
    for name, field in queryset.model.__dict__.items():
        if not isinstance(field, GenericForeignKey):
            continue
        fks[name] = field
    return fks


def _content_type_to_content_mapping_for_gfks(queryset, gfks):
    """
    Build mapping of content_type -> [content_pk] for the given queryset and
    its generic foreign keys.
    """
    data = collections.defaultdict(list)
    for (
        _model,
        _field_name,
        content_type,
        object_pk,
    ) in _queryset_gfk_content_generator(queryset, gfks):
        if content_type and object_pk:
            data[content_type].append(object_pk)
    return data


def _get_related_content_type_and_related_object_pk(model, fk):
    """Get related object's pk and content type."""

    try:
        related_content_type = getattr(model, fk.ct_field,)
        related_object_id = getattr(model, fk.fk_field)
    except TypeError:
        related_object_id = None
        related_content_type = None
    except ContentType.DoesNotExist:
        related_object_id = None
        related_content_type = None

    return related_content_type, related_object_id


def _queryset_gfk_content_generator(queryset, gfks):
    """
    Generator function that yields information about all GenericForeignKey
    fields for all models of a queryset.
    """
    for model in queryset:
        data = namedtuple(
            "data", ["model", "field_name", "content_type", "object_pk"]
        )
        for field_name, field in gfks.items():
            (
                content_type,
                object_pk,
            ) = _get_related_content_type_and_related_object_pk(model, field)
            yield data(model, field_name, content_type, object_pk)


def prefetch_generic_foreign_key_objects(queryset):
    """Prefetch generic foreign key objects."""
    gfks = _queryset_foreign_keys(queryset)
    gfks_data = _content_type_to_content_mapping_for_gfks(queryset, gfks)
    for content_type, object_pks in gfks_data.items():
        gfk_models = prefetch_generic_foreign_key_objects(
            content_type.model_class()
            .objects.filter(pk__in=object_pks)
            .select_related()
        )
        for gfk_model in gfk_models:
            for data in _queryset_gfk_content_generator(queryset, gfks):
                if data.content_type != content_type:
                    continue
                if data.object_pk != str(gfk_model.pk):
                    continue

                setattr(data.model, data.field_name, gfk_model)

    return queryset
