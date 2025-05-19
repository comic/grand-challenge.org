from django.db import migrations


def create_session_utilizations(apps, schema_editor):
    SessionCost = apps.get_model("workstations", "SessionCost")  # noqa: N806
    SessionUtilization = apps.get_model(  # noqa: N806
        "utilization", "SessionUtilization"
    )
    for session_cost in SessionCost.objects.iterator():
        session_utilization = SessionUtilization.objects.create(
            created=session_cost.created,
            modified=session_cost.modified,
            session=session_cost.session,
            duration=session_cost.duration,
            creator=session_cost.creator,
            interactive_algorithms=session_cost.interactive_algorithms,
        )
        session_utilization.reader_studies.set(
            session_cost.reader_studies.all()
        )


class Migration(migrations.Migration):

    dependencies = [
        ("utilization", "0001_initial"),
        (
            "workstations",
            "0027_feedbackgroupobjectpermission_workstation_group_i_ac4715_idx_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(create_session_utilizations, elidable=True),
    ]
