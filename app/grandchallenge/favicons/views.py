from django.http import Http404
from django.views.generic import RedirectView
from favicon.models import Favicon


class FaviconView(RedirectView):
    """
    Some browsers do not follow the favicon links in base.html, so do this
    explicitly here.
    """

    permanent = False
    rel = "shortcut icon"

    def get_redirect_url(self, *args, **kwargs):
        fav = Favicon.objects.filter(isFavicon=True).first()

        if not fav:
            raise Http404

        if self.rel == "shortcut icon":
            size = 32
        else:
            # This is the largest icon from
            # https://github.com/audreyr/favicon-cheat-sheet
            size = kwargs.get("size", 180)

        default_fav = fav.get_favicon(size=size, rel=self.rel)

        return default_fav.faviconImage.url
