from django.contrib import admin

from grandchallenge.studies.admin import StudyInline
from .models import Patient


class PatientInline(admin.StackedInline):
    model = Patient
    extra = 0


class PatientAdmin(admin.ModelAdmin):
    fieldsets = []
    inlines = [StudyInline]
    search_fields = ("name",)


admin.site.register(Patient, PatientAdmin)
