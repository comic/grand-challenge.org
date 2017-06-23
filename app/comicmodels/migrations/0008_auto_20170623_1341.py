# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0007_auto_20170614_1134'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comicsite',
            options={'verbose_name': 'challenge', 'verbose_name_plural': 'challenges'},
        ),
        migrations.AlterModelOptions(
            name='projectmetadata',
            options={'verbose_name': 'project metadata', 'verbose_name_plural': 'project metadata'},
        ),
    ]
