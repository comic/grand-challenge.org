# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filetransfers', '0001_squashed_0002_auto_20170609_1253'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UploadModel',
        ),
    ]
