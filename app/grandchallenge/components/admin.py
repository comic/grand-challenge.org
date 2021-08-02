from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class ComponentImageAdmin(GuardedModelAdmin):
    exclude = ("image",)
    readonly_fields = ("creator",)
    list_display = (
        "pk",
        "created",
        "creator",
        "ready",
        "image_sha256",
        "requires_gpu",
        "requires_memory_gb",
        "status",
    )
    list_filter = (
        "ready",
        "requires_gpu",
    )
    search_fields = ("pk", "creator__username", "image_sha256")


class ComponentInterfaceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "slug",
        "kind",
        "default_value",
        "relative_path",
        "schema",
        "store_in_database",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("store_in_database", *self.readonly_fields)
        else:
            return self.readonly_fields


class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")


admin.site.register(ComponentInterface, ComponentInterfaceAdmin)
admin.site.register(ComponentInterfaceValue, ComponentInterfaceValueAdmin)
