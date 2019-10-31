from django.contrib import admin

from grandchallenge.patients.models import Patient
from grandchallenge.studies.admin import StudyInline


class PatientInline(admin.StackedInline):
    model = Patient
    extra = 0


class PatientAdmin(admin.ModelAdmin):
    fieldsets = []
    inlines = [StudyInline]
    search_fields = ("name",)


admin.site.register(Patient, PatientAdmin)
