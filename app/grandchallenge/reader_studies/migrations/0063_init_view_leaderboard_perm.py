from django.db import migrations


def init_view_leaderboard_permission(apps, _schema_editor):
    ReaderStudy = apps.get_model("reader_studies", "ReaderStudy")  # noqa: N806

    for rs in ReaderStudy.objects.filter(is_educational=True).all():
        rs.save()


class Migration(migrations.Migration):
    dependencies = [
        (
            "reader_studies",
            "0062_readerstudy_leaderboard_accessible_to_readers",
        ),
    ]

    operations = [
        migrations.RunPython(init_view_leaderboard_permission, elidable=True),
    ]
