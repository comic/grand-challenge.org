from django.contrib import admin

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductBasic,
    ProductEntry,
)


admin.site.register(CompanyEntry)
admin.site.register(ProductBasic)
admin.site.register(ProductEntry)
