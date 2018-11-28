from django.contrib import admin
from .models import Patient
from grandchallenge.studies.admin import StudyInline


class PatientInline(admin.StackedInline):
    model = Patient
    extra = 0


class PatientAdmin(admin.ModelAdmin):
    fieldsets = []
    inlines = [StudyInline]
    search_fields = ("name",)
    # list_filter = ("sex", "birth_date")


admin.site.register(Patient, PatientAdmin)
