# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jqfileupload.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StagedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('csrf', models.CharField(max_length=128)),
                ('client_id', models.CharField(max_length=128, null=True)),
                ('client_filename', models.CharField(max_length=128)),
                ('file_id', models.UUIDField()),
                ('timeout', models.DateTimeField()),
                ('file', models.FileField(upload_to=jqfileupload.models.generate_upload_filename)),
                ('start_byte', models.BigIntegerField()),
                ('end_byte', models.BigIntegerField()),
                ('total_size', models.BigIntegerField(null=True)),
            ],
        ),
    ]
