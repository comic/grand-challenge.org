# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0013_auto_20171214_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_score_default_sort',
            field=models.CharField(max_length=4, default='desc', choices=[('asc', 'Ascending'), ('desc', 'Descending')], help_text='The default sorting to use for the scores on the results page.'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_score_jsonpath',
            field=models.CharField(max_length=255, blank=True, help_text='The jsonpath of the field in metrics.json that will be used for the overall scores on the results page. See http://goessner.net/articles/JsonPath/ for syntax.'),
        ),
    ]
