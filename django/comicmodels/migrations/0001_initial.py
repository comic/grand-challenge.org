# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import re
import ckeditor.fields
import django.utils.timezone
from django.conf import settings
import django.core.validators
import comicmodels.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ComicSite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_name', models.SlugField(default=b'', help_text=b'short name used in url, specific css, files etc. No spaces allowed', validators=[comicmodels.models.validate_nounderscores, django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')])),
                ('skin', models.CharField(default=b'public_html/project.css', help_text=b'css file to include throughout this project. relative to project data folder', max_length=225)),
                ('description', models.CharField(default=b'', help_text=b'Short summary of this project, max 1024 characters.', max_length=1024, blank=True)),
                ('logo', models.CharField(default=b'public_html/logo.png', help_text=b'100x100 pixel image file to use as logo in projects overview. Relative to project datafolder', max_length=255)),
                ('header_image', models.CharField(help_text=b'optional 658 pixel wide Header image which will appear on top of each project page top of each project. Relative to project datafolder. Suggested default:public_html/header.png', max_length=255, blank=True)),
                ('hidden', models.BooleanField(default=True, help_text=b'Do not display this Project in any public overview')),
                ('hide_signin', models.BooleanField(default=False, help_text=b'Do no show the Sign in / Register link on any page')),
                ('hide_footer', models.BooleanField(default=False, help_text=b'Do not show the general links or the grey divider line in page footers')),
                ('disclaimer', models.CharField(default=b'', max_length=2048, null=True, help_text=b"Optional text to show on each page in the project. For showing 'under construction' type messages", blank=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, auto_now_add=True)),
                ('workshop_date', models.DateField(help_text=b'Date on which the workshop belonging to this project will be held', null=True, blank=True)),
                ('event_name', models.CharField(default=b'', max_length=1024, null=True, help_text=b'The name of the event the workshop will be held at', blank=True)),
                ('event_url', models.URLField(help_text=b'Website of the event which will host the workshop', null=True, blank=True)),
                ('is_open_for_submissions', models.BooleanField(default=False, help_text=b'This project currently accepts new submissions. Affects listing in projects overview')),
                ('submission_page_name', models.CharField(help_text=b'If the project allows submissions, there will be a link in projects overview going directly to you project/<submission_page_name>/. If empty, the projects main page will be used instead', max_length=255, null=True, blank=True)),
                ('number_of_submissions', models.IntegerField(help_text=b'The number of submissions have been evalutated for this project', null=True, blank=True)),
                ('last_submission_date', models.DateField(help_text=b'When was the last submission evaluated?', null=True, blank=True)),
                ('offers_data_download', models.BooleanField(default=False, help_text=b'This project currently accepts new submissions. Affects listing in projects overview')),
                ('number_of_downloads', models.IntegerField(help_text=b'How often has the dataset for this project been downloaded?', null=True, blank=True)),
                ('publication_url', models.URLField(help_text=b'URL of a publication describing this project', null=True, blank=True)),
                ('publication_journal_name', models.CharField(help_text=b"If publication was in a journal, please list the journal name here We use <a target='new' href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed journal abbreviations</a> format", max_length=225, null=True, blank=True)),
                ('require_participant_review', models.BooleanField(default=False, help_text=b'If ticked, new participants need to be approved by project admins before they can access restricted pages. If not ticked, new users are allowed access immediately')),
            ],
            options={
                'verbose_name': 'project',
                'verbose_name_plural': 'projects',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DropboxFolder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.SlugField(max_length=64, blank=True)),
                ('permission_lvl', models.CharField(default=b'ALL', max_length=3, choices=[(b'ALL', b'All'), (b'REG', b'Registered users only'), (b'ADM', b'Administrators only')])),
                ('access_token_key', models.CharField(default=b'', max_length=255, blank=True)),
                ('access_token_secret', models.CharField(default=b'', max_length=255, blank=True)),
                ('last_status_msg', models.CharField(default=b'', max_length=1023, blank=True)),
                ('comicsite', models.ForeignKey(help_text=b'To which comicsite does this object belong?', to='comicmodels.ComicSite')),
            ],
            options={
                'abstract': False,
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileSystemDataset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.SlugField(max_length=64, blank=True)),
                ('permission_lvl', models.CharField(default=b'ALL', max_length=3, choices=[(b'ALL', b'All'), (b'REG', b'Registered users only'), (b'ADM', b'Administrators only')])),
                ('description', models.TextField()),
                ('folder', models.FilePathField()),
                ('comicsite', models.ForeignKey(help_text=b'To which comicsite does this object belong?', to='comicmodels.ComicSite')),
            ],
            options={
                'abstract': False,
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.SlugField(max_length=64, blank=True)),
                ('permission_lvl', models.CharField(default=b'ALL', max_length=3, choices=[(b'ALL', b'All'), (b'REG', b'Registered users only'), (b'ADM', b'Administrators only')])),
                ('order', models.IntegerField(default=1, help_text=b'Determines order in which page appear in site menu', editable=False)),
                ('display_title', models.CharField(default=b'', help_text=b'On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used', max_length=255, blank=True)),
                ('hidden', models.BooleanField(default=False, help_text=b'Do not display this page in site menu')),
                ('html', ckeditor.fields.RichTextField()),
                ('comicsite', models.ForeignKey(help_text=b'To which comicsite does this object belong?', to='comicmodels.ComicSite')),
            ],
            options={
                'ordering': ['comicsite', 'order'],
                'abstract': False,
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectMetaData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contact_name', models.CharField(default=b'', help_text=b'Who is the main contact person for this project?', max_length=255)),
                ('contact_email', models.EmailField(help_text=b'', max_length=75)),
                ('title', models.CharField(default=b'', help_text=b'Project title, will be printed in bold in projects overview', max_length=255)),
                ('URL', models.URLField(help_text=b'URL of the main page of the project')),
                ('description', models.TextField(default=b'', help_text=b'Max 350 characters. Will be used in projects overview', max_length=350, blank=True, validators=[django.core.validators.MaxLengthValidator(350)])),
                ('event_name', models.CharField(default=b'', help_text=b'Name of the event this project is associated with, if any', max_length=255, blank=True)),
                ('event_URL', models.URLField(help_text=b'URL of the event this project is associated to, if any', null=True, blank=True)),
                ('submission_deadline', models.DateField(help_text=b'Deadline for submitting results to this project', null=True, blank=True)),
                ('workshop_date', models.DateField(null=True, blank=True)),
                ('open_for_submissions', models.BooleanField(default=False, help_text=b'This project accepts and evaluates submissions')),
                ('submission_URL', models.URLField(help_text=b'Direct URL to a page where you can submit results', null=True, blank=True)),
                ('offers_data_download', models.BooleanField(default=False, help_text=b"Data can be downloaded from this project's website")),
                ('download_URL', models.URLField(help_text=b'Direct URL to a page where this data can be downloaded', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RegistrationRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=datetime.date.today, auto_now_add=True)),
                ('changed', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default=b'PEND', max_length=4, choices=[(b'PEND', b'Pending'), (b'ACPT', b'Accepted'), (b'RJCT', b'Rejected')])),
                ('project', models.ForeignKey(help_text=b'To which project does the user want to register?', to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(help_text=b'which user requested to participate?', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UploadModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.SlugField(max_length=64, blank=True)),
                ('permission_lvl', models.CharField(default=b'ALL', max_length=3, choices=[(b'ALL', b'All'), (b'REG', b'Registered users only'), (b'ADM', b'Administrators only')])),
                ('file', models.FileField(max_length=255, upload_to=comicmodels.models.giveFileUploadDestinationPath)),
                ('created', models.DateTimeField(default=datetime.date.today, auto_now_add=True)),
                ('modified', models.DateTimeField(default=datetime.date.today, auto_now=True)),
                ('comicsite', models.ForeignKey(help_text=b'To which comicsite does this object belong?', to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(help_text=b'which user uploaded this?', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'uploaded file',
                'verbose_name_plural': 'uploaded files',
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='page',
            unique_together=set([('comicsite', 'title')]),
        ),
    ]
