# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import ckeditor.fields
import comicmodels.models
from django.conf import settings
import django.utils.timezone
import django.core.validators
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComicSite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('short_name', models.SlugField(default=b'', help_text=b'short name used in url, specific css, files etc. No spaces allowed', validators=[comicmodels.models.validate_nounderscores, django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z', 32), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')])),
                ('skin', models.CharField(max_length=225, default=b'public_html/project.css', help_text=b'css file to include throughout this project. relative to project data folder')),
                ('description', models.CharField(max_length=1024, blank=True, default=b'', help_text=b'Short summary of this project, max 1024 characters.')),
                ('logo', models.CharField(max_length=255, default=b'public_html/logo.png', help_text=b'100x100 pixel image file to use as logo in projects overview. Relative to project datafolder')),
                ('header_image', models.CharField(max_length=255, blank=True, help_text=b'optional 658 pixel wide Header image which will appear on top of each project page top of each project. Relative to project datafolder. Suggested default:public_html/header.png')),
                ('hidden', models.BooleanField(default=True, help_text=b'Do not display this Project in any public overview')),
                ('hide_signin', models.BooleanField(default=False, help_text=b'Do no show the Sign in / Register link on any page')),
                ('hide_footer', models.BooleanField(default=False, help_text=b'Do not show the general links or the grey divider line in page footers')),
                ('disclaimer', models.CharField(max_length=2048, blank=True, null=True, default=b'', help_text=b"Optional text to show on each page in the project. For showing 'under construction' type messages")),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, auto_now_add=True)),
                ('workshop_date', models.DateField(blank=True, null=True, help_text=b'Date on which the workshop belonging to this project will be held')),
                ('event_name', models.CharField(max_length=1024, blank=True, null=True, default=b'', help_text=b'The name of the event the workshop will be held at')),
                ('event_url', models.URLField(blank=True, null=True, help_text=b'Website of the event which will host the workshop')),
                ('is_open_for_submissions', models.BooleanField(default=False, help_text=b'This project currently accepts new submissions. Affects listing in projects overview')),
                ('submission_page_name', models.CharField(max_length=255, blank=True, null=True, help_text=b'If the project allows submissions, there will be a link in projects overview going directly to you project/<submission_page_name>/. If empty, the projects main page will be used instead')),
                ('number_of_submissions', models.IntegerField(blank=True, null=True, help_text=b'The number of submissions have been evalutated for this project')),
                ('last_submission_date', models.DateField(blank=True, null=True, help_text=b'When was the last submission evaluated?')),
                ('offers_data_download', models.BooleanField(default=False, help_text=b'This project currently accepts new submissions. Affects listing in projects overview')),
                ('number_of_downloads', models.IntegerField(blank=True, null=True, help_text=b'How often has the dataset for this project been downloaded?')),
                ('publication_url', models.URLField(blank=True, null=True, help_text=b'URL of a publication describing this project')),
                ('publication_journal_name', models.CharField(max_length=225, blank=True, null=True, help_text=b"If publication was in a journal, please list the journal name here We use <a target='new' href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed journal abbreviations</a> format")),
                ('require_participant_review', models.BooleanField(default=False, help_text=b'If ticked, new participants need to be approved by project admins before they can access restricted pages. If not ticked, new users are allowed access immediately')),
            ],
            options={
                'verbose_name': 'project',
                'verbose_name_plural': 'projects',
            },
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('title', models.SlugField(max_length=64, blank=True)),
                ('permission_lvl', models.CharField(max_length=3, default=b'ALL', choices=[(b'ALL', b'All'), (b'REG', b'Registered users only'), (b'ADM', b'Administrators only')])),
                ('order', models.IntegerField(default=1, editable=False, help_text=b'Determines order in which page appear in site menu')),
                ('display_title', models.CharField(max_length=255, blank=True, default=b'', help_text=b'On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used')),
                ('hidden', models.BooleanField(default=False, help_text=b'Do not display this page in site menu')),
                ('html', ckeditor.fields.RichTextField()),
                ('comicsite', models.ForeignKey(help_text=b'To which comicsite does this object belong?', to='comicmodels.ComicSite')),
            ],
            options={
                'ordering': ['comicsite', 'order'],
                'abstract': False,
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
        ),
        migrations.CreateModel(
            name='ProjectMetaData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('contact_name', models.CharField(max_length=255, default='', help_text='Who is the main contact person for this project?')),
                ('contact_email', models.EmailField(max_length=254)),
                ('title', models.CharField(max_length=255, default='', help_text='Project title, will be printed in bold in projects overview')),
                ('URL', models.URLField(help_text='URL of the main page of the project')),
                ('description', models.TextField(max_length=350, blank=True, default='', help_text='Max 350 characters. Will be used in projects overview', validators=[django.core.validators.MaxLengthValidator(350)])),
                ('event_name', models.CharField(max_length=255, blank=True, default='', help_text='Name of the event this project is associated with, if any')),
                ('event_URL', models.URLField(blank=True, null=True, help_text='URL of the event this project is associated to, if any')),
                ('submission_deadline', models.DateField(blank=True, null=True, help_text='Deadline for submitting results to this project')),
                ('workshop_date', models.DateField(blank=True, null=True)),
                ('open_for_submissions', models.BooleanField(default=False, help_text='This project accepts and evaluates submissions')),
                ('submission_URL', models.URLField(blank=True, null=True, help_text='Direct URL to a page where you can submit results')),
                ('offers_data_download', models.BooleanField(default=False, help_text="Data can be downloaded from this project's website")),
                ('download_URL', models.URLField(blank=True, null=True, help_text='Direct URL to a page where this data can be downloaded')),
            ],
        ),
        migrations.CreateModel(
            name='RegistrationRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('changed', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(max_length=4, default='PEND', choices=[('PEND', 'Pending'), ('ACPT', 'Accepted'), ('RJCT', 'Rejected')])),
                ('project', models.ForeignKey(help_text='To which project does the user want to register?', to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(help_text='which user requested to participate?', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UploadModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('title', models.SlugField(max_length=64)),
                ('permission_lvl', models.CharField(max_length=3, default='ALL', choices=[('ALL', 'All'), ('REG', 'Registered users only'), ('ADM', 'Administrators only')])),
                ('file', models.FileField(max_length=255, upload_to=comicmodels.models.giveFileUploadDestinationPath)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('comicsite', models.ForeignKey(help_text='To which comicsite does this object belong?', to='comicmodels.ComicSite')),
                ('user', models.ForeignKey(help_text='which user uploaded this?', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'uploaded file',
                'verbose_name_plural': 'uploaded files',
                'permissions': (('view_ComicSiteModel', 'Can view Comic Site Model'),),
            },
        ),
        migrations.AlterUniqueTogether(
            name='page',
            unique_together=set([('comicsite', 'title')]),
        ),
        migrations.AlterField(
            model_name='page',
            name='title',
            field=models.SlugField(max_length=64),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='short_name',
            field=models.SlugField(unique=True, default=b'', help_text=b'short name used in url, specific css, files etc. No spaces allowed', validators=[comicmodels.models.validate_nounderscores, django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z', 32), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid'), django.core.validators.MinLengthValidator(1)]),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='description',
            field=models.CharField(max_length=1024, blank=True, default='', help_text='Short summary of this project, max 1024 characters.'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='disclaimer',
            field=models.CharField(max_length=2048, blank=True, null=True, default='', help_text="Optional text to show on each page in the project. For showing 'under construction' type messages"),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='event_name',
            field=models.CharField(max_length=1024, blank=True, null=True, default='', help_text='The name of the event the workshop will be held at'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='event_url',
            field=models.URLField(blank=True, null=True, help_text='Website of the event which will host the workshop'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='header_image',
            field=models.CharField(max_length=255, blank=True, help_text='optional 658 pixel wide Header image which will appear on top of each project page top of each project. Relative to project datafolder. Suggested default:public_html/header.png'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='hidden',
            field=models.BooleanField(default=True, help_text='Do not display this Project in any public overview'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='hide_footer',
            field=models.BooleanField(default=False, help_text='Do not show the general links or the grey divider line in page footers'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='hide_signin',
            field=models.BooleanField(default=False, help_text='Do no show the Sign in / Register link on any page'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='is_open_for_submissions',
            field=models.BooleanField(default=False, help_text='This project currently accepts new submissions. Affects listing in projects overview'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='last_submission_date',
            field=models.DateField(blank=True, null=True, help_text='When was the last submission evaluated?'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='logo',
            field=models.CharField(max_length=255, default='public_html/logo.png', help_text='100x100 pixel image file to use as logo in projects overview. Relative to project datafolder'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='number_of_downloads',
            field=models.IntegerField(blank=True, null=True, help_text='How often has the dataset for this project been downloaded?'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='number_of_submissions',
            field=models.IntegerField(blank=True, null=True, help_text='The number of submissions have been evalutated for this project'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='offers_data_download',
            field=models.BooleanField(default=False, help_text='This project currently accepts new submissions. Affects listing in projects overview'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='publication_journal_name',
            field=models.CharField(max_length=225, blank=True, null=True, help_text="If publication was in a journal, please list the journal name here We use <a target='new' href='https://www.ncbi.nlm.nih.gov/nlmcatalog/journals'>PubMed journal abbreviations</a> format"),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='publication_url',
            field=models.URLField(blank=True, null=True, help_text='URL of a publication describing this project'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='require_participant_review',
            field=models.BooleanField(default=False, help_text='If ticked, new participants need to be approved by project admins before they can access restricted pages. If not ticked, new users are allowed access immediately'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='short_name',
            field=models.SlugField(unique=True, default='', help_text='short name used in url, specific css, files etc. No spaces allowed', validators=[comicmodels.models.validate_nounderscores, django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z', 32), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid'), django.core.validators.MinLengthValidator(1)]),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='skin',
            field=models.CharField(max_length=225, default='public_html/project.css', help_text='css file to include throughout this project. relative to project data folder'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='submission_page_name',
            field=models.CharField(max_length=255, blank=True, null=True, help_text='If the project allows submissions, there will be a link in projects overview going directly to you project/<submission_page_name>/. If empty, the projects main page will be used instead'),
        ),
        migrations.AlterField(
            model_name='comicsite',
            name='workshop_date',
            field=models.DateField(blank=True, null=True, help_text='Date on which the workshop belonging to this project will be held'),
        ),
        migrations.AlterField(
            model_name='page',
            name='comicsite',
            field=models.ForeignKey(help_text='To which comicsite does this object belong?', to='comicmodels.ComicSite'),
        ),
        migrations.AlterField(
            model_name='page',
            name='display_title',
            field=models.CharField(max_length=255, blank=True, default='', help_text='On pages and in menu items, use this text. Spaces and special chars allowed here. Optional field. If emtpy, title is used'),
        ),
        migrations.AlterField(
            model_name='page',
            name='hidden',
            field=models.BooleanField(default=False, help_text='Do not display this page in site menu'),
        ),
        migrations.AlterField(
            model_name='page',
            name='order',
            field=models.IntegerField(default=1, editable=False, help_text='Determines order in which page appear in site menu'),
        ),
        migrations.AlterField(
            model_name='page',
            name='permission_lvl',
            field=models.CharField(max_length=3, default='ALL', choices=[('ALL', 'All'), ('REG', 'Registered users only'), ('ADM', 'Administrators only')]),
        ),
        migrations.AlterModelOptions(
            name='comicsite',
            options={'verbose_name': 'challenge', 'verbose_name_plural': 'challenges'},
        ),
        migrations.AlterModelOptions(
            name='projectmetadata',
            options={'verbose_name': 'project metadata', 'verbose_name_plural': 'project metadata'},
        ),
        migrations.AddField(
            model_name='comicsite',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='ProjectMetaData',
        ),
        migrations.AddField(
            model_name='comicsite',
            name='use_evaluation',
            field=models.BooleanField(default=False, help_text='If true, use the automated evaluation system. See the evaluation page created in the Challenge site.'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='admins_group',
            field=models.OneToOneField(null=True, editable=False, related_name='admins_of_challenge', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='participants_group',
            field=models.OneToOneField(null=True, editable=False, related_name='participants_of_challenge', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='registration_page_text',
            field=models.TextField(blank=True, default='', help_text='The text to use on the registration page, you could include a data usage agreement here. You can use HTML markup here.'),
        ),
        migrations.AddField(
            model_name='comicsite',
            name='title',
            field=models.CharField(max_length=64, blank=True, default='', help_text='The name of the challenge that is displayed on the All Challenges page. If this is blank the short name of the challenge will be used.'),
        ),
    ]
