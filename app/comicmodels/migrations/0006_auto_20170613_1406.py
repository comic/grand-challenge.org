# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0005_auto_20170609_1253'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dropboxfolder',
            name='comicsite',
        ),
        migrations.DeleteModel(
            name='DropboxFolder',
        ),
    ]
