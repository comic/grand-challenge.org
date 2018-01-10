# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import social_django.fields


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0013_auto_20171214_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_extra_results_columns',
            field=social_django.fields.JSONField(default=dict, help_text='A JSON object that contains the extra columns from metrics.json that will be displayed on the results page. Where the KEYS contain the titles of the columns, and the VALUES contain the JsonPath to the corresponding metric in metrics.json. For example:\n\n{"Accuracy": "aggregates.acc","Dice": "dice.mean"}'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_score_default_sort',
            field=models.CharField(max_length=4, default='desc', choices=[('asc', 'Ascending'), ('desc', 'Descending')], help_text='The default sorting to use for the scores on the results page.'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_score_jsonpath',
            field=models.CharField(max_length=255, blank=True, help_text='The jsonpath of the field in metrics.json that will be used for the overall scores on the results page. See http://goessner.net/articles/JsonPath/ for syntax. For example:\n\ndice.mean'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='evaluation_score_title',
            field=models.CharField(max_length=32, default='Score', help_text='The name that will be displayed for the scores column, for instance:\n\nScore (log-loss)'),
        ),
    ]
