# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import social_django.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0016_comicsite_title'),
        ('evaluation', '0002_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ranking',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('ranks', social_django.fields.JSONField(default=dict, editable=False, help_text='Keeps track of the ranking of the evaluation results.')),
                ('challenge', models.OneToOneField(editable=False, related_name='evaluation_ranking', to='comicmodels.ComicSite')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='config',
            name='ranks',
        ),
        migrations.AddField(
            model_name='config',
            name='allow_submission_comments',
            field=models.BooleanField(default=False, help_text='Allow users to submit comments as part of their submission.'),
        ),
        migrations.AddField(
            model_name='submission',
            name='comment',
            field=models.CharField(max_length=128, blank=True, default='', help_text='You can add a comment here to help you keep track of your submissions.'),
        ),
    ]
