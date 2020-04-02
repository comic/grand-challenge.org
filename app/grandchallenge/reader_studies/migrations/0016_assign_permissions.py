from django.db import migrations


def add_change_permissions(apps, schema_editor):
    Answer = apps.get_model("reader_studies", "Answer")  # noqa: N806
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    try:
        change_answer = Permission.objects.get(
            content_type__app_label="reader_studies", codename="change_answer"
        )
    except Permission.DoesNotExist:
        # We are running tests
        return
    UserObjectPermission = apps.get_model(  # noqa: N806
        "guardian", "UserObjectPermission"
    )
    ContentType = apps.get_model("contenttypes", "ContentType")  # noqa: N806
    content_type_id = ContentType.objects.get_for_model(Answer).id

    for answer in Answer.objects.all():
        UserObjectPermission.objects.create(
            permission=change_answer,
            user=answer.creator,
            object_pk=answer.pk,
            content_type_id=content_type_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("reader_studies", "0015_auto_20200401_1449"),
        ("guardian", "0002_generic_permissions_index"),
    ]

    operations = [
        migrations.RunPython(add_change_permissions, migrations.RunPython.noop)
    ]
