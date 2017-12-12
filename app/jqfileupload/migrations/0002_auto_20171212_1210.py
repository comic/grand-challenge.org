# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jqfileupload.models


class Migration(migrations.Migration):

    dependencies = [
        ('jqfileupload', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stagedfile',
            name='file',
            field=models.FileField(upload_to=jqfileupload.models.generate_upload_filename),
        ),
    ]
