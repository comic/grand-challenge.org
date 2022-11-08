from django.contrib import admin

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    BooleanClassificationAnnotationGroupObjectPermission,
    BooleanClassificationAnnotationUserObjectPermission,
    ETDRSGridAnnotation,
    ETDRSGridAnnotationGroupObjectPermission,
    ETDRSGridAnnotationUserObjectPermission,
    ImagePathologyAnnotationGroupObjectPermission,
    ImagePathologyAnnotationUserObjectPermission,
    ImageQualityAnnotationGroupObjectPermission,
    ImageQualityAnnotationUserObjectPermission,
    ImageTextAnnotation,
    ImageTextAnnotationGroupObjectPermission,
    ImageTextAnnotationUserObjectPermission,
    LandmarkAnnotationSet,
    LandmarkAnnotationSetGroupObjectPermission,
    LandmarkAnnotationSetUserObjectPermission,
    MeasurementAnnotation,
    MeasurementAnnotationGroupObjectPermission,
    MeasurementAnnotationUserObjectPermission,
    OctRetinaImagePathologyAnnotation,
    OctRetinaImagePathologyAnnotationGroupObjectPermission,
    OctRetinaImagePathologyAnnotationUserObjectPermission,
    PolygonAnnotationSet,
    PolygonAnnotationSetGroupObjectPermission,
    PolygonAnnotationSetUserObjectPermission,
    RetinaImagePathologyAnnotation,
    RetinaImagePathologyAnnotationGroupObjectPermission,
    RetinaImagePathologyAnnotationUserObjectPermission,
    SingleLandmarkAnnotation,
    SingleLandmarkAnnotationGroupObjectPermission,
    SingleLandmarkAnnotationUserObjectPermission,
    SinglePolygonAnnotation,
    SinglePolygonAnnotationGroupObjectPermission,
    SinglePolygonAnnotationUserObjectPermission,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)


class BooleanClassificationAnnotationAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "name", "created")
    list_filter = ("created", "value", "name")


class SinglePolygonAnnotationInline(admin.StackedInline):
    model = SinglePolygonAnnotation
    extra = 0
    readonly_fields = ("annotation_set", "value", "z", "interpolated")


class PolygonAnnotationSetAdmin(admin.ModelAdmin):
    search_fields = (
        "grader__username",
        "created",
        "name",
        "image__name",
        "id",
    )
    list_filter = ("created", "name")
    inlines = [SinglePolygonAnnotationInline]
    readonly_fields = ("grader", "image", "created")


class SingleLandmarkAnnotationInline(admin.StackedInline):
    model = SingleLandmarkAnnotation
    extra = 0
    readonly_fields = ("image", "landmarks")


class LandmarkAnnotationSetAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "created")
    list_filter = ("created",)
    inlines = [SingleLandmarkAnnotationInline]
    readonly_fields = ("grader", "created")


class AbstractImageAnnotationAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "image__name")
    readonly_fields = ("grader", "image")


admin.site.register(ETDRSGridAnnotation, AbstractImageAnnotationAdmin)
admin.site.register(MeasurementAnnotation)
admin.site.register(
    BooleanClassificationAnnotation, BooleanClassificationAnnotationAdmin
)
admin.site.register(PolygonAnnotationSet, PolygonAnnotationSetAdmin)
admin.site.register(SinglePolygonAnnotation)
admin.site.register(
    SinglePolygonAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    SinglePolygonAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(LandmarkAnnotationSet, LandmarkAnnotationSetAdmin)
admin.site.register(SingleLandmarkAnnotation)
admin.site.register(
    RetinaImagePathologyAnnotation, AbstractImageAnnotationAdmin
)
admin.site.register(
    OctRetinaImagePathologyAnnotation, AbstractImageAnnotationAdmin
)
admin.site.register(ImageTextAnnotation, AbstractImageAnnotationAdmin)
admin.site.register(
    ImagePathologyAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ImagePathologyAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    BooleanClassificationAnnotationUserObjectPermission,
    UserObjectPermissionAdmin,
)
admin.site.register(
    BooleanClassificationAnnotationGroupObjectPermission,
    GroupObjectPermissionAdmin,
)
admin.site.register(
    MeasurementAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    MeasurementAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    PolygonAnnotationSetUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    PolygonAnnotationSetGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    ImageTextAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ImageTextAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    OctRetinaImagePathologyAnnotationUserObjectPermission,
    UserObjectPermissionAdmin,
)
admin.site.register(
    OctRetinaImagePathologyAnnotationGroupObjectPermission,
    GroupObjectPermissionAdmin,
)
admin.site.register(
    SingleLandmarkAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    SingleLandmarkAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    ImageQualityAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ImageQualityAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    RetinaImagePathologyAnnotationUserObjectPermission,
    UserObjectPermissionAdmin,
)
admin.site.register(
    RetinaImagePathologyAnnotationGroupObjectPermission,
    GroupObjectPermissionAdmin,
)
admin.site.register(
    LandmarkAnnotationSetUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    LandmarkAnnotationSetGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    ETDRSGridAnnotationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ETDRSGridAnnotationGroupObjectPermission, GroupObjectPermissionAdmin
)
