from django.db import migrations
from django.db.models import F


def create_evaluation_utilizations(apps, schema_editor):
    Evaluation = apps.get_model("evaluation", "Evaluation")  # noqa: N806
    EvaluationUtilization = apps.get_model(  # noqa: N806
        "evaluation", "EvaluationUtilization"
    )
    for evaluation in Evaluation.objects.annotate(
        duration=F("completed_at") - F("started_at")
    ).iterator():
        EvaluationUtilization.objects.create(
            evaluation=evaluation,
            external_evaluation=evaluation.submission.phase.external_evaluation,
            duration=evaluation.duration,
            compute_cost_euro_millicents=evaluation.compute_cost_euro_millicents,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0088_evaluationutilization"),
    ]

    operations = [
        migrations.RunPython(create_evaluation_utilizations, elidable=True),
    ]
