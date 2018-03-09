from django.views.generic import ListView

from comicmodels.models import UploadModel
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from pages.views import ComicSiteFilteredQuerysetMixin


class UploadList(UserIsChallengeAdminMixin, ComicSiteFilteredQuerysetMixin,
                 ListView):
    model = UploadModel
