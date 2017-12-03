# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import evaluation.validators
import evaluation.models
import uuid
from django.conf import settings
import social_django.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0010_delete_projectmetadata'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                ('image', models.FileField(help_text='Tar archive of the container image produced from the command `docker save IMAGE > IMAGE.tar`. See https://docs.docker.com/engine/reference/commandline/save/', validators=[evaluation.validators.MimeTypeValidator(allowed_types=('application/x-tarbinary', 'application/x-tar')), evaluation.validators.ContainerImageValidator(single_image=True)], upload_to=evaluation.models.method_image_path)),
                ('image_sha256', models.CharField(max_length=71, editable=False)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
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
                ('job', models.OneToOneField(to='evaluation.Job')),
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
            name='StagedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('csrf', models.CharField(max_length=128)),
                ('client_id', models.CharField(max_length=128, null=True)),
                ('client_filename', models.CharField(max_length=128)),
                ('file_id', models.UUIDField()),
                ('timeout', models.DateTimeField()),
                ('file', models.FileField(upload_to='')),
                ('start_byte', models.BigIntegerField()),
                ('end_byte', models.BigIntegerField()),
                ('total_size', models.BigIntegerField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(validators=[evaluation.validators.MimeTypeValidator(allowed_types=('application/zip',))], upload_to=evaluation.models.submission_file_path)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='job',
            name='method',
            field=models.ForeignKey(to='evaluation.Method'),
        ),
        migrations.AddField(
            model_name='job',
            name='submission',
            field=models.ForeignKey(to='evaluation.Submission'),
        ),
        migrations.AlterUniqueTogether(
            name='method',
            unique_together=set([('challenge', 'image_sha256')]),
        ),
    ]
