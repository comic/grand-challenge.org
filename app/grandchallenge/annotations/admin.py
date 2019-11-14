from django.contrib import admin

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    ETDRSGridAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    PolygonAnnotationSet,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
)


class BooleanClassificationAnnotationAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "name", "created")
    list_filter = ("created", "value", "name")


class SinglePolygonAnnotationInline(admin.StackedInline):
    model = SinglePolygonAnnotation
    extra = 0


class PolygonAnnotationSetAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "created", "name")
    list_filter = ("created", "grader__username", "name")
    inlines = [SinglePolygonAnnotationInline]


class SingleLandmarkAnnotationInline(admin.StackedInline):
    model = SingleLandmarkAnnotation
    extra = 0


class LandmarkAnnotationSetAdmin(admin.ModelAdmin):
    search_fields = ("grader__username", "created")
    list_filter = ("created", "grader__username")
    inlines = [SingleLandmarkAnnotationInline]


admin.site.register(ETDRSGridAnnotation)
admin.site.register(MeasurementAnnotation)
admin.site.register(
    BooleanClassificationAnnotation, BooleanClassificationAnnotationAdmin
)
admin.site.register(PolygonAnnotationSet, PolygonAnnotationSetAdmin)
admin.site.register(SinglePolygonAnnotation)
admin.site.register(LandmarkAnnotationSet, LandmarkAnnotationSetAdmin)
admin.site.register(SingleLandmarkAnnotation)
