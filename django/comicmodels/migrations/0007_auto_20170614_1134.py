# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0006_auto_20170613_1406'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filesystemdataset',
            name='comicsite',
        ),
        migrations.DeleteModel(
            name='FileSystemDataset',
        ),
    ]
