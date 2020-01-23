from django.contrib import admin
from django.contrib.auth.models import User, Group
from guardian.admin import GuardedModelAdmin
from django.contrib.auth.admin import UserAdmin as OriginalUserAdmin

from comic.eyra.models import JobInput, Algorithm, Job, Benchmark, Submission, DataFile, DataSet


class AlgorithmAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created',)


admin.site.register(Algorithm, AlgorithmAdmin)


class JobInputsInline(admin.TabularInline):
    model = JobInput


class JobAdmin(admin.ModelAdmin):
    list_display = ('status', 'created')
    inlines = [JobInputsInline]


admin.site.register(Job, JobAdmin)


class BenchmarkAdmin(GuardedModelAdmin):
    list_display = ('name', 'creator', 'created')


admin.site.register(Benchmark, BenchmarkAdmin)


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')


admin.site.register(Submission, SubmissionAdmin)


class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'size', 'creator', 'created')


admin.site.register(DataFile, DataFileAdmin)


class DataSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created')


admin.site.register(DataSet, DataSetAdmin)


class UserAdmin(OriginalUserAdmin, GuardedModelAdmin):
    pass


class UserInLine(admin.TabularInline):
    model = User.groups.through
    extra = 0


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class GroupAdmin(GuardedModelAdmin):
    list_display = ('name',)
    list_filter = ()
    inlines = [UserInLine]
    filter_horizontal = ('permissions',)


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
