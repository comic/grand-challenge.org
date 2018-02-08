# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0014_comicsite_registration_page_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comicsite',
            name='registration_page_text',
            field=models.TextField(blank=True, default='', help_text='The text to use on the registration page, you could include a data usage agreement here. You can use HTML markup here.'),
        ),
    ]
