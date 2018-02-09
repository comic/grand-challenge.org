# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0015_auto_20180208_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='title',
            field=models.CharField(max_length=64, blank=True, default='', help_text='The name of the challenge that is displayed on the All Challenges page. If this is blank the short name of the challenge will be used.'),
        ),
    ]
