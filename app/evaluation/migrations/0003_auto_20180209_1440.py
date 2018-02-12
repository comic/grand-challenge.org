# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0002_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='allow_submission_comments',
            field=models.BooleanField(default=False, help_text='Allow users to submit comments as part of their submission.'),
        ),
        migrations.AddField(
            model_name='submission',
            name='comment',
            field=models.CharField(max_length=128, blank=True, default='', help_text='You can add a comment here to help you keep track of your submissions.'),
        ),
    ]
