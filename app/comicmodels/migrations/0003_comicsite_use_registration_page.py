# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0002_auto_20180307_0803'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='use_registration_page',
            field=models.BooleanField(default=True, help_text='If true, show a registration page on the challenge site.'),
        ),
    ]
