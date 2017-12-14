# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('comicmodels', '0011_comicsite_use_evaluation'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='admins_group',
            field=models.OneToOneField(blank=True, null=True, editable=False, related_name='admins_of_challenge', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='participants_group',
            field=models.OneToOneField(blank=True, null=True, editable=False, related_name='participants_of_challenge', to='auth.Group'),
        ),
    ]
