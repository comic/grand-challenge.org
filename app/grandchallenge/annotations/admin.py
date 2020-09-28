from django.contrib import admin

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    ETDRSGridAnnotation,
    ImageTextAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    OctRetinaImagePathologyAnnotation,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
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
admin.site.register(LandmarkAnnotationSet, LandmarkAnnotationSetAdmin)
admin.site.register(SingleLandmarkAnnotation)
admin.site.register(
    RetinaImagePathologyAnnotation, AbstractImageAnnotationAdmin
)
admin.site.register(
    OctRetinaImagePathologyAnnotation, AbstractImageAnnotationAdmin
)
admin.site.register(ImageTextAnnotation, AbstractImageAnnotationAdmin)
