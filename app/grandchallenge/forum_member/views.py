from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.views.generic import RedirectView


class ForumProfileDetailView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        user = get_object_or_404(klass=get_user_model(), pk=self.kwargs["pk"])
        return user.user_profile.get_absolute_url()
