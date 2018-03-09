from django.views.generic import ListView

from comicmodels.models import UploadModel
from comicsite.permissions.mixins import UserIsChallengeAdminMixin


class UploadList(UserIsChallengeAdminMixin, ListView):
    model = UploadModel
