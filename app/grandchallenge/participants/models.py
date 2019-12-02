from django.db import models

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import RequestBase


class RegistrationRequest(RequestBase):
    """
    When a user wants to join a project, admins have the option of reviewing
    each user before allowing or denying them. This class records the needed
    info for that.
    """

    challenge = models.ForeignKey(
        Challenge,
        help_text="To which project does the user want to register?",
        on_delete=models.CASCADE,
    )

    @property
    def object_name(self):
        return self.challenge.short_name

    def __str__(self):
        return f"{self.challenge.short_name} registration request by user {self.user.username}"

    class Meta:
        unique_together = (("challenge", "user"),)
