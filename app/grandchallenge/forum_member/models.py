# Custom models should be declared before importing
# django-machina models

# noinspection PyUnresolvedReferences
from machina.apps.forum_member.models import *  # noqa: F401, F403
