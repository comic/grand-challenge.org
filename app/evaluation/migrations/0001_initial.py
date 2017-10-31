# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import uuid
import social_django.fields
import evaluation.models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('comicmodels', '0008_auto_20170623_1341'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('status', models.PositiveSmallIntegerField(default=0, choices=[(0, 'The task is waiting for execution'), (1, 'The task has been started'), (2, 'The task is to be retried, possibly because of failure'), (3, 'The task raised an exception, or has exceeded the retry limit'), (4, 'The task executed successfully'), (5, 'The task was cancelled')])),
                ('status_history', social_django.fields.JSONField(default=dict)),
                ('output', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Method',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('image_repository', models.CharField(max_length=128)),
                ('image_tag', models.CharField(max_length=64)),
                ('image_sha256', models.CharField(max_length=64)),
                ('version', models.PositiveIntegerField(default=0)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('metrics', social_django.fields.JSONField(default=dict)),
                ('public', models.BooleanField(default=True)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('method', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='evaluation.Method')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ResultScreenshot',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(upload_to=evaluation.models.result_screenshot_path)),
                ('result', models.ForeignKey(to='evaluation.Result')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(upload_to=evaluation.models.challenge_submission_path)),
                ('description', models.FileField(upload_to=evaluation.models.challenge_submission_path)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='job',
            name='method',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='evaluation.Method'),
        ),
        migrations.AddField(
            model_name='job',
            name='submission',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='evaluation.Submission'),
        ),
        migrations.AlterUniqueTogether(
            name='method',
            unique_together=set([('challenge', 'version')]),
        ),
    ]
