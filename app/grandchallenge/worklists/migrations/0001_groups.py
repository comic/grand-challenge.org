from django.db import migrations
from django.contrib.auth.models import Group
from django.conf import settings


def create_worklist_groups(apps, schema_editor):
    Group.objects.create(name=settings.WORKLIST_ACCESS_GROUP_NAME)


class Migration(migrations.Migration):
    dependencies = []
    operations = [migrations.RunPython(create_worklist_groups)]
