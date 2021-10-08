from django.contrib import admin

from grandchallenge.patients.models import Patient


class PatientInline(admin.StackedInline):
    model = Patient
    extra = 0


class PatientAdmin(admin.ModelAdmin):
    fieldsets = []
    search_fields = ("name",)


admin.site.register(Patient, PatientAdmin)
