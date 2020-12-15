from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.organizations.models import Organization

admin.site.register(Organization, GuardedModelAdmin)
