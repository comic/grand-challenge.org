# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stagedfile',
            name='client_filename',
            field=models.CharField(max_length=128, default='xxx'),
            preserve_default=False,
        ),
    ]
