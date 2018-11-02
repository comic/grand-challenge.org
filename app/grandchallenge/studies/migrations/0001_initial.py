from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Study',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, null=True, max_length=100, verbose_name='The identifier code for this study.')),
                ('region_of_interest', models.CharField(blank=True, null=True, max_length=255, verbose_name='Region or location where the study was performed.')),
            ],
        )
    ]
