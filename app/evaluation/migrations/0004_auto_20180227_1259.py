# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import evaluation.validators


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0003_config_use_teams'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='file',
            field=models.FileField(validators=[evaluation.validators.MimeTypeValidator(allowed_types=('application/zip', 'text/plain')), evaluation.validators.ExtensionValidator(allowed_extensions=('.zip', '.csv'))], upload_to=evaluation.models.submission_file_path),
        ),
    ]
