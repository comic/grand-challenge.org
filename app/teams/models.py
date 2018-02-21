from django.conf import settings
from django.db import models

from comicsite.core.urlresolvers import reverse
from evaluation.models import UUIDModel


class Team(models.Model):
    name = models.CharField(max_length=32, unique=True)
    challenge = models.ForeignKey(
        'comicmodels.ComicSite',
        on_delete=models.CASCADE,
        editable=False,
    )
    logo = models.ImageField(blank=True)
    website = models.URLField(blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)

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
    pending = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            ('user', 'team'),
        )

    def validate_unique(self, exclude=None):
        # TODO: make sure that user is only part of 1 team per challenge
        super(TeamMember, self).validate_unique(exclude)
