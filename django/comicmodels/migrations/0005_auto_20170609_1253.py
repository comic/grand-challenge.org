# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import re
import comicmodels.models
import django.core.validators
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0004_auto_20170607_1229'),
    ]

    operations = [
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
            model_name='dropboxfolder',
            name='access_token_key',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='dropboxfolder',
            name='access_token_secret',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='dropboxfolder',
            name='comicsite',
            field=models.ForeignKey(help_text='To which comicsite does this object belong?', to='comicmodels.ComicSite'),
        ),
        migrations.AlterField(
            model_name='dropboxfolder',
            name='last_status_msg',
            field=models.CharField(max_length=1023, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='dropboxfolder',
            name='permission_lvl',
            field=models.CharField(max_length=3, default='ALL', choices=[('ALL', 'All'), ('REG', 'Registered users only'), ('ADM', 'Administrators only')]),
        ),
        migrations.AlterField(
            model_name='filesystemdataset',
            name='comicsite',
            field=models.ForeignKey(help_text='To which comicsite does this object belong?', to='comicmodels.ComicSite'),
        ),
        migrations.AlterField(
            model_name='filesystemdataset',
            name='permission_lvl',
            field=models.CharField(max_length=3, default='ALL', choices=[('ALL', 'All'), ('REG', 'Registered users only'), ('ADM', 'Administrators only')]),
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
        migrations.AlterField(
            model_name='projectmetadata',
            name='URL',
            field=models.URLField(help_text='URL of the main page of the project'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='contact_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='contact_name',
            field=models.CharField(max_length=255, default='', help_text='Who is the main contact person for this project?'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='description',
            field=models.TextField(max_length=350, blank=True, default='', help_text='Max 350 characters. Will be used in projects overview', validators=[django.core.validators.MaxLengthValidator(350)]),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='download_URL',
            field=models.URLField(blank=True, null=True, help_text='Direct URL to a page where this data can be downloaded'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='event_URL',
            field=models.URLField(blank=True, null=True, help_text='URL of the event this project is associated to, if any'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='event_name',
            field=models.CharField(max_length=255, blank=True, default='', help_text='Name of the event this project is associated with, if any'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='offers_data_download',
            field=models.BooleanField(default=False, help_text="Data can be downloaded from this project's website"),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='open_for_submissions',
            field=models.BooleanField(default=False, help_text='This project accepts and evaluates submissions'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='submission_URL',
            field=models.URLField(blank=True, null=True, help_text='Direct URL to a page where you can submit results'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='submission_deadline',
            field=models.DateField(blank=True, null=True, help_text='Deadline for submitting results to this project'),
        ),
        migrations.AlterField(
            model_name='projectmetadata',
            name='title',
            field=models.CharField(max_length=255, default='', help_text='Project title, will be printed in bold in projects overview'),
        ),
        migrations.AlterField(
            model_name='registrationrequest',
            name='project',
            field=models.ForeignKey(help_text='To which project does the user want to register?', to='comicmodels.ComicSite'),
        ),
        migrations.AlterField(
            model_name='registrationrequest',
            name='status',
            field=models.CharField(max_length=4, default='PEND', choices=[('PEND', 'Pending'), ('ACPT', 'Accepted'), ('RJCT', 'Rejected')]),
        ),
        migrations.AlterField(
            model_name='registrationrequest',
            name='user',
            field=models.ForeignKey(help_text='which user requested to participate?', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='comicsite',
            field=models.ForeignKey(help_text='To which comicsite does this object belong?', to='comicmodels.ComicSite'),
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='permission_lvl',
            field=models.CharField(max_length=3, default='ALL', choices=[('ALL', 'All'), ('REG', 'Registered users only'), ('ADM', 'Administrators only')]),
        ),
        migrations.AlterField(
            model_name='uploadmodel',
            name='user',
            field=models.ForeignKey(help_text='which user uploaded this?', to=settings.AUTH_USER_MODEL),
        ),
    ]
