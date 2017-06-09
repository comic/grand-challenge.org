# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filetransfers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadmodel',
            name='file',
            field=models.FileField(upload_to='uploads/%Y/%m/%d/%H/%M/%S/'),
        ),
    ]
