# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import evaluation.models
import evaluation.validators


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0002_stagedfile_client_filename'),
    ]

    operations = [
        migrations.RenameField(
            model_name='method',
            old_name='user',
            new_name='creator',
        ),
        migrations.AlterField(
            model_name='method',
            name='image',
            field=models.FileField(help_text='Tar archive of the container image produced from the command `docker save IMAGE > IMAGE.tar`. See https://docs.docker.com/engine/reference/commandline/save/', validators=[evaluation.validators.MimeTypeValidator(allowed_types=('application/x-tarbinary', 'application/x-tar')), evaluation.validators.ContainerImageValidator(single_image=True)], upload_to=evaluation.models.method_image_path),
        ),
        migrations.AlterUniqueTogether(
            name='method',
            unique_together=set([('challenge', 'image_sha256')]),
        ),
    ]
