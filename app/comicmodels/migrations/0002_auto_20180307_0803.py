# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0001_squashed_0016_comicsite_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationrequest',
            name='changed',
            field=models.DateTimeField(default=datetime.datetime(2018, 3, 7, 8, 3, 20, 233255, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='registrationrequest',
            unique_together=set([('project', 'user')]),
        ),
    ]
