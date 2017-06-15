# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import re
import django.core.validators
import comicmodels.models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0002_auto_20170606_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comicsite',
            name='short_name',
            field=models.SlugField(default=b'', validators=[comicmodels.models.validate_nounderscores, django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid'), django.core.validators.MinLengthValidator(1)], help_text=b'short name used in url, specific css, files etc. No spaces allowed', unique=True),
            preserve_default=True,
        ),
    ]
