from django.contrib import admin

from grandchallenge.eyra_data.models import DataFile, DataType


class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created')


class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'original_file_name', 'creator', 'created')


admin.site.register(DataFile, DataFileAdmin)
admin.site.register(DataType, DataTypeAdmin)
