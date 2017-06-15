# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('comicmodels', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dropboxfolder',
            name='title',
            field=models.SlugField(max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filesystemdataset',
            name='title',
            field=models.SlugField(max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='page',
            name='title',
            field=models.SlugField(max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='title',
            field=models.SlugField(max_length=64),
            preserve_default=True,
        ),
    ]
