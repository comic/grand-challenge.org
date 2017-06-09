# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='privacy',
            field=models.CharField(verbose_name='privacy', max_length=15, default='registered', choices=[('open', 'Open'), ('registered', 'Registered'), ('closed', 'Closed')], help_text='Designates who can view your profile.'),
        ),
    ]
