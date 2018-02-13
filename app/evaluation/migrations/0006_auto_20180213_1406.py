# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0005_auto_20180213_0928'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='allow_supplementary_file',
            field=models.BooleanField(default=False, help_text='Show a supplementary file field on the submissions page so that users can upload an additional file along with their predictions file as part of their submission (eg, include a pdf description of their method).'),
        ),
        migrations.AlterField(
            model_name='config',
            name='require_supplementary_file',
            field=models.BooleanField(default=False, help_text='Force users to upload a supplementary file with their predictions file.'),
        ),
    ]
