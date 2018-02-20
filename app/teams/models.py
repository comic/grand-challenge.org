from django.conf import settings
from django.db import models

# Create your models here.
from comicsite.core.urlresolvers import reverse
from evaluation.models import UUIDModel


class Config(models.Model):
    pass


class Team(models.Model):
    name = models.CharField(max_length=32, unique=True)
    challenge = models.ForeignKey(
        'comicmodels.ComicSite',
        on_delete=models.CASCADE,
        editable=False,
    )
    logo = models.ImageField(blank=True)
    website = models.URLField(blank=True)

    def get_absolute_url(self):
        return reverse('teams:detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })


class TeamMember(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    is_admin = models.BooleanField()
