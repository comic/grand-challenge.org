from django.contrib import admin

from grandchallenge.eyra_algorithms.models import Algorithm, Input, Job, JobInput, Interface


class AlgorithmAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created', 'interface')


class InterfaceInputsInlineAdmin(admin.TabularInline):
    model = Input


class InterfaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'created')
    inlines = [InterfaceInputsInlineAdmin]


class JobInputsInline(admin.TabularInline):
    model = JobInput


class JobAdmin(admin.ModelAdmin):
    list_display = ('status', 'created')
    inlines = [JobInputsInline]


admin.site.register(Algorithm, AlgorithmAdmin)
admin.site.register(Interface, InterfaceAdmin)
admin.site.register(Job, JobAdmin)
