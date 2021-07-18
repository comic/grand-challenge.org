import collections
from collections import namedtuple

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
)


# Code in this file was adapted from https://djangosnippets.org/snippets/2492/
# and https://andrew.hawker.io/writings/2020/11/18/django-activity-stream-prefetch-generic-foreign-key/


def _queryset_foreign_keys(queryset, nested):
    """
    Build mapping of name -> field for GenericForeignKey or
    ForwardManyToOneDescript fields on the queryset.
    """
    fks = {}
    for name, field in queryset.model.__dict__.items():
        if nested and not isinstance(field, ForwardManyToOneDescriptor):
            continue
        elif not nested and not isinstance(field, GenericForeignKey):
            continue
        fks[name] = field
    return fks


def _content_type_to_content_mapping_for_nested_gfks(queryset, fks):
    """
    Build mapping of content_type -> [content_pk] for the given queryset and
    its nested generic foreign keys.
    """
    data = collections.defaultdict(list)
    gfks = {}
    for weak_model in queryset:
        for _, fk_field in fks.items():
            for name, fk in fk_field.field.related_model.__dict__.items():
                if not isinstance(fk, GenericForeignKey):
                    continue
                gfks[name] = fk
                (
                    related_content_type,
                    related_object_id,
                ) = _get_related_content_type_and_related_object_pk(
                    weak_model.action, fk_field.field.related_model, fk
                )
                if related_content_type is None:
                    continue
                if related_object_id is None:
                    continue

                data[related_content_type].append(related_object_id)
    return data, gfks


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
        data[content_type].append(object_pk)
    return data


def _get_related_content_type_and_related_object_pk(model, fk_field, fk):
    """Get related object's pk and content type."""

    try:
        related_content_type_id = getattr(
            model, fk_field._meta.get_field(fk.ct_field).get_attname(),
        )
        related_object_id = getattr(model, fk.fk_field)
        related_content_type = ContentType.objects.get_for_id(
            related_content_type_id
        )
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
            ) = _get_related_content_type_and_related_object_pk(
                model, field.model, field
            )
            yield data(model, field_name, content_type, object_pk)


def prefetch_nested_generic_foreign_key_objects(queryset):
    """Prefetch nested generic foreign key objects."""
    fks = _queryset_foreign_keys(queryset, nested=True)
    data, gfks = _content_type_to_content_mapping_for_nested_gfks(
        queryset, fks
    )

    for content_type, object_ids in data.items():
        model_class = content_type.model_class()
        models = prefetch_nested_generic_foreign_key_objects(
            model_class.objects.filter(pk__in=object_ids).select_related()
        )
        for model in models:
            for weak_model in queryset:
                for gfk_name, gfk_field in gfks.items():
                    (
                        related_content_type,
                        related_object_id,
                    ) = _get_related_content_type_and_related_object_pk(
                        weak_model.action, gfk_field.model, gfk_field
                    )
                    if related_object_id != model.pk:
                        continue
                    if related_content_type != content_type:
                        continue
                    setattr(weak_model.action, gfk_name, model)

    return queryset


def prefetch_generic_foreign_key_objects(queryset):
    """Prefetch generic foreign key objects."""
    gfks = _queryset_foreign_keys(queryset, nested=False)
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
