from django.contrib import admin

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductEntry,
)


admin.site.register(CompanyEntry)
admin.site.register(ProductEntry)
