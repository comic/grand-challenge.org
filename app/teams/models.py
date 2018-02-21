from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from comicsite.core.urlresolvers import reverse
from evaluation.models import UUIDModel


class Team(models.Model):
    name = models.CharField(max_length=32)
    challenge = models.ForeignKey(
        'comicmodels.ComicSite',
        on_delete=models.CASCADE,
        editable=False,
    )
    logo = models.ImageField(blank=True)
    website = models.URLField(blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'challenge'),
        )

    def validate_unique(self, exclude=None):
        super(Team, self).validate_unique(exclude)
        if not any(x in exclude for x in
                   ['challenge', 'creator']) and TeamMember.objects.filter(
            team__challenge=self.challenge,
            user=self.creator).exists():
            raise ValidationError(
                'You are already a member of another team for this challenge')

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Team, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('teams:detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })

    def get_members(self):
        User = get_user_model()
        return User.objects.filter(teammember__team=self)


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
        super(TeamMember, self).validate_unique(exclude)
        if not any(x in exclude for x in
                   ['user', 'team']) and TeamMember.objects.filter(
            team__challenge=self.team.challenge,
            user=self.user).exists():
            raise ValidationError(
                'You are already a member of another team for this challenge')

    def save(self, *args, **kwargs):
        self.full_clean()
        super(TeamMember, self).save(*args, **kwargs)
