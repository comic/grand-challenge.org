from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("evaluation", "0077_create_evaluation_input_set"),
    ]

    operations = [
        # Remove the old field
        migrations.RemoveField(
            model_name="evaluation",
            name="inputs",
        ),
        # Rename the temporary field to the final name
        migrations.RenameField(
            model_name="evaluation",
            old_name="input_set",
            new_name="inputs",
        ),
        migrations.AlterUniqueTogether(
            name="evaluation",
            unique_together={
                (
                    "submission",
                    "method",
                    "inputs",
                    "ground_truth",
                    "time_limit",
                    "requires_gpu_type",
                    "requires_memory_gb",
                )
            },
        ),
    ]
