from django.contrib import admin

from grandchallenge.products.models import (
    Company,
    Product,
)


admin.site.register(Company)
admin.site.register(Product)
