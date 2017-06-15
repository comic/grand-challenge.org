# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0003_auto_20170606_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comicsite',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='contact_email',
            field=models.EmailField(help_text=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='registrationrequest',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
