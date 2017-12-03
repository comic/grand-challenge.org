# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0010_delete_projectmetadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='use_evaluation',
            field=models.BooleanField(default=False, help_text='If true, use the automated evaluation system. See the evaluation page created in the Challenge site.'),
        ),
    ]
