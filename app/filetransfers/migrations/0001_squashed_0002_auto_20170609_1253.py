# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('filetransfers', '0001_initial'), ('filetransfers', '0002_auto_20170609_1253')]

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UploadModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('title', models.CharField(max_length=64, blank=True)),
                ('file', models.FileField(upload_to='uploads/%Y/%m/%d/%H/%M/%S/')),
            ],
        ),
    ]
