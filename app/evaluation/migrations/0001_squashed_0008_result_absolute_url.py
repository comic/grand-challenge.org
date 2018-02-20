# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import social_django.fields
import evaluation.models
import evaluation.validators
from django.conf import settings
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('evaluation', '0001_initial'), ('evaluation', '0002_config'), ('evaluation', '0003_auto_20180212_1205'), ('evaluation', '0004_auto_20180212_1629'), ('evaluation', '0005_auto_20180213_0928'), ('evaluation', '0006_auto_20180213_1406'), ('evaluation', '0007_auto_20180216_1516'), ('evaluation', '0008_result_absolute_url')]

    dependencies = [
        ('comicmodels', '0001_squashed_0016_comicsite_title'),
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
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
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
                ('ready', models.BooleanField(default=False, editable=False, help_text='Is this method ready to be used?')),
                ('status', models.TextField(editable=False)),
                ('image', models.FileField(help_text='Tar archive of the container image produced from the command `docker save IMAGE > IMAGE.tar`. See https://docs.docker.com/engine/reference/commandline/save/', validators=[evaluation.validators.ExtensionValidator(allowed_extensions=('.tar',))], upload_to=evaluation.models.method_image_path)),
                ('image_sha256', models.CharField(max_length=71, editable=False)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
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
                ('job', models.OneToOneField(null=True, to='evaluation.Job')),
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
                ('file', models.FileField(validators=[evaluation.validators.MimeTypeValidator(allowed_types=('application/zip',))], upload_to=evaluation.models.submission_file_path)),
                ('challenge', models.ForeignKey(to='comicmodels.ComicSite')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('comment', models.CharField(max_length=128, blank=True, default='', help_text='You can add a comment here to help you keep track of your submissions.')),
                ('supplementary_file', models.FileField(blank=True, validators=[evaluation.validators.MimeTypeValidator(allowed_types=('text/plain', 'application/pdf'))], upload_to=evaluation.models.submission_supplementary_file_path)),
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
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('score_jsonpath', models.CharField(max_length=255, blank=True, help_text='The jsonpath of the field in metrics.json that will be used for the overall scores on the results page. See http://goessner.net/articles/JsonPath/ for syntax. For example:\n\ndice.mean')),
                ('score_title', models.CharField(max_length=32, default='Score', help_text='The name that will be displayed for the scores column, for instance:\n\nScore (log-loss)')),
                ('score_default_sort', models.CharField(max_length=4, default='desc', choices=[('asc', 'Ascending'), ('desc', 'Descending')], help_text='The default sorting to use for the scores on the results page.')),
                ('extra_results_columns', social_django.fields.JSONField(default=dict, help_text='A JSON object that contains the extra columns from metrics.json that will be displayed on the results page. Where the KEYS contain the titles of the columns, and the VALUES contain the JsonPath to the corresponding metric in metrics.json. For example:\n\n{"Accuracy": "aggregates.acc","Dice": "dice.mean"}')),
                ('challenge', models.OneToOneField(editable=False, related_name='evaluation_config', to='comicmodels.ComicSite')),
                ('allow_submission_comments', models.BooleanField(default=False, help_text='Allow users to submit comments as part of their submission.')),
                ('require_supplementary_file', models.BooleanField(default=False, help_text='Force users to upload a supplementary file with their predictions file.')),
                ('supplementary_file_help_text', models.CharField(max_length=128, blank=True, default='', help_text='The help text to include on the submissions page to describe the submissions file. Eg: "A PDF description of the method.".')),
                ('show_supplementary_file_link', models.BooleanField(default=False, help_text='Show a link to download the supplementary file on the results page.')),
                ('supplementary_file_label', models.CharField(max_length=32, blank=True, default='Supplementary File', help_text='The label that will be used on the submission and results page for the supplementary file. For example: Algorithm Description.')),
                ('allow_supplementary_file', models.BooleanField(default=False, help_text='Show a supplementary file field on the submissions page so that users can upload an additional file along with their predictions file as part of their submission (eg, include a pdf description of their method).')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='result',
            name='rank',
            field=models.PositiveIntegerField(default=0, help_text='The position of this result on the leaderboard. If the value is zero, then the result is unranked.'),
        ),
        migrations.AddField(
            model_name='result',
            name='absolute_url',
            field=models.TextField(blank=True, editable=False),
        ),
    ]
