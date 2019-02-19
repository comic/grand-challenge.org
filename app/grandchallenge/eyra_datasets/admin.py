from django.contrib import admin

from grandchallenge.eyra_datasets.models import DataSet, DataSetType, DataSetTypeFile


class DataSetTypeFilesInline(admin.TabularInline):
    model = DataSetTypeFile

class DataSetTypeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'created')
    inlines = [DataSetTypeFilesInline]

class FileTypeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'created')

admin.site.register(DataSet)
admin.site.register(DataSetType, DataSetTypeAdmin)
