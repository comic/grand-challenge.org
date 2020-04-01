from django.db import migrations


def create_dicom_group(apps, schema_editor):
    Answer = apps.get_model("reader_studies", "Answer")  # noqa: N806
    for answer in Answer.objects.all():
        answer.assign_permissions()


class Migration(migrations.Migration):

    dependencies = [
        ("reader_studies", "0015_auto_20200401_1449"),
    ]

    operations = [
        migrations.RunPython(create_dicom_group, migrations.RunPython.noop)
    ]
