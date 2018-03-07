# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0001_squashed_0016_comicsite_title'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='registrationrequest',
            unique_together=set([('project', 'user')]),
        ),
    ]
