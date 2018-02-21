# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('comicmodels', '0001_squashed_0016_comicsite_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=32)),
                ('department', models.CharField(max_length=64, blank=True)),
                ('institution', models.CharField(max_length=64, blank=True)),
                ('website', models.URLField(blank=True)),
                ('challenge', models.ForeignKey(editable=False, to='comicmodels.ComicSite')),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('pending', models.BooleanField(default=True)),
                ('team', models.ForeignKey(to='teams.Team')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together=set([('user', 'team')]),
        ),
        migrations.AlterUniqueTogether(
            name='team',
            unique_together=set([('name', 'challenge')]),
        ),
    ]
