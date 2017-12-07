# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0009_comicsite_creator'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ProjectMetaData',
        ),
    ]
