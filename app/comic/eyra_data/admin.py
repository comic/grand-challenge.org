from django.contrib import admin

from comic.eyra_data.models import DataFile, DataType, DataSet


class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created')


class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'size', 'creator', 'created')

class DataSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')


admin.site.register(DataFile, DataFileAdmin)
admin.site.register(DataType, DataTypeAdmin)
admin.site.register(DataSet, DataSetAdmin)
