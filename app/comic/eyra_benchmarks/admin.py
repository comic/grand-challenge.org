from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from comic.eyra_benchmarks.models import Benchmark, Submission


class BenchmarkAdmin(GuardedModelAdmin):
    list_display = ('name', 'creator', 'created')


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')


admin.site.register(Benchmark, BenchmarkAdmin)
admin.site.register(Submission, SubmissionAdmin)
