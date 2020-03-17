from rest_framework import filters

from grandchallenge.retina_api.mixins import is_in_retina_admins_group


class RetinaAnnotationFilter(filters.BaseFilterBackend):
    """
    Filter backend that only returns objects that belong to the current user, except
    if the user is in the `retina_admins` group.

    This filter is created for annotation models and requires that the model has a
    `grader` field that defines the user that is the owner of the object. As defined
    in `annotations.AbstractAnnotationModel`.
    """

    def filter_queryset(self, request, queryset, view):
        if is_in_retina_admins_group(request.user):
            return queryset
        return queryset.filter(grader=request.user)


class ImageAnnotationFilter(filters.BaseFilterBackend):
    """
    Filter backend that only returns objects that belong to the image that
    is supplied by the image_id query parameter.
    """

    def filter_queryset(self, request, queryset, view):
        image_id = request.query_params.get("image_id")
        if image_id is not None:
            return queryset.filter(image__id=image_id)
        return queryset
