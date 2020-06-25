from django.contrib import admin

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class ComponentInterfaceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "slug",
        "kind",
        "default_value",
        "relative_path",
    )
    readonly_fields = (
        "default_value",
        "relative_path",
    )


class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")


admin.site.register(ComponentInterface, ComponentInterfaceAdmin)
admin.site.register(ComponentInterfaceValue, ComponentInterfaceValueAdmin)
