import collections

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
)


# Code in this file was adapted from https://djangosnippets.org/snippets/2492/
# and https://andrew.hawker.io/writings/2020/11/18/django-activity-stream-prefetch-generic-foreign-key/


def _queryset_foreign_keys(queryset, generic_fk):
    fks = {}
    for name, field in queryset.model.__dict__.items():
        if not generic_fk and not isinstance(
            field, ForwardManyToOneDescriptor
        ):
            continue
        elif generic_fk and not isinstance(field, GenericForeignKey):
            continue
        fks[name] = field
    return fks


def _content_type_to_content_mapping_for_nested_gfks(queryset, fks):
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
    related_content_type_id = getattr(
        model, fk_field._meta.get_field(fk.ct_field).get_attname(),
    )
    try:
        related_object_id = int(getattr(model, fk.fk_field))
        related_content_type = ContentType.objects.get_for_id(
            related_content_type_id
        )
    except TypeError:
        related_object_id = None
        related_content_type = None

    return related_content_type, related_object_id


def _queryset_gfk_content_generator(queryset, gfks):
    for model in queryset:
        for field_name, field in gfks.items():
            (
                content_type,
                object_pk,
            ) = _get_related_content_type_and_related_object_pk(
                model, field.model, field
            )
            yield (model, field_name, content_type, object_pk)


def prefetch_notification_action(queryset):
    fks = _queryset_foreign_keys(queryset, generic_fk=False)
    data, gfks = _content_type_to_content_mapping_for_nested_gfks(
        queryset, fks
    )

    for content_type, object_ids in data.items():
        model_class = content_type.model_class()
        models = prefetch_notification_action(
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
    gfks = _queryset_foreign_keys(queryset, generic_fk=True)
    gfks_data = _content_type_to_content_mapping_for_gfks(queryset, gfks)

    for content_type, object_pks in gfks_data.items():
        gfk_models = prefetch_generic_foreign_key_objects(
            content_type.model_class()
            .objects.filter(pk__in=object_pks)
            .select_related()
        )
        for gfk_model in gfk_models:
            for gfk in _queryset_gfk_content_generator(queryset, gfks):
                qs_model, gfk_field_name, gfk_content_type, gfk_object_pk = gfk

                if gfk_content_type != content_type:
                    continue
                if gfk_object_pk != str(gfk_model.pk):
                    continue

                setattr(qs_model, gfk_field_name, gfk_model)

    return queryset
