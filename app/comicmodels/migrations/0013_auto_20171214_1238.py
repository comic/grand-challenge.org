# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0012_auto_20171214_1045'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comicsite',
            name='admins_group',
            field=models.OneToOneField(null=True, editable=False, related_name='admins_of_challenge', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='participants_group',
            field=models.OneToOneField(null=True, editable=False, related_name='participants_of_challenge', to='auth.Group'),
        ),
    ]
