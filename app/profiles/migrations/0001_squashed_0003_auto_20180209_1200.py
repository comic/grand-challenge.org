# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import easy_thumbnails.fields
import userena.models
from django.conf import settings
import django_countries.fields


class Migration(migrations.Migration):

    replaces = [('profiles', '0001_initial'), ('profiles', '0002_auto_20170609_1253'), ('profiles', '0003_auto_20180209_1200')]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('mugshot', easy_thumbnails.fields.ThumbnailerImageField(verbose_name='mugshot', blank=True, help_text='A personal image displayed in your profile.', upload_to=userena.models.upload_to_mugshot)),
                ('privacy', models.CharField(verbose_name='privacy', max_length=15, default='open', choices=[('open', 'Open'), ('registered', 'Registered'), ('closed', 'Closed')], help_text='Designates who can view your profile.')),
                ('institution', models.CharField(max_length=100)),
                ('department', models.CharField(max_length=100)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('website', models.CharField(max_length=150, blank=True)),
                ('user', models.OneToOneField(verbose_name='user', related_name='user_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'permissions': (('view_profile', 'Can view profile'),),
            },
        ),
    ]
