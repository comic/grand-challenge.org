from django.contrib import admin

from grandchallenge.eyra_benchmarks.models import Benchmark, Submission


class BenchmarkAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'created')


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'created')


admin.site.register(Benchmark, BenchmarkAdmin)
admin.site.register(Submission, SubmissionAdmin)
