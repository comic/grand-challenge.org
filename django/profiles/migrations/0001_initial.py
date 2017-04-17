# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import easy_thumbnails.fields
import django_countries.fields
import userena.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('mugshot', easy_thumbnails.fields.ThumbnailerImageField(help_text='A personal image displayed in your profile.', upload_to=userena.models.upload_to_mugshot, verbose_name='mugshot', blank=True)),
                ('privacy', models.CharField(default=b'registered', help_text='Designates who can view your profile.', max_length=15, verbose_name='privacy', choices=[(b'open', 'Open'), (b'registered', 'Registered'), (b'closed', 'Closed')])),
                ('institution', models.CharField(max_length=100)),
                ('department', models.CharField(max_length=100)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('website', models.CharField(max_length=150, blank=True)),
                ('user', models.OneToOneField(related_name='user_profile', verbose_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'permissions': (('view_profile', 'Can view profile'),),
            },
            bases=(models.Model,),
        ),
    ]
