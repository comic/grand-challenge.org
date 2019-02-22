from django.contrib import admin

from grandchallenge.eyra_algorithms.models import Algorithm, AlgorithmInput, Job, JobInput


class AlgorithmInputsInlineAdmin(admin.TabularInline):
    model = AlgorithmInput


class AlgorithmAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')
    inlines = [AlgorithmInputsInlineAdmin]


class JobInputsInline(admin.TabularInline):
    model = JobInput


class JobAdmin(admin.ModelAdmin):
    list_display = ('status', 'created')
    inlines = [JobInputsInline]


admin.site.register(Algorithm, AlgorithmAdmin)
admin.site.register(Job, JobAdmin)
