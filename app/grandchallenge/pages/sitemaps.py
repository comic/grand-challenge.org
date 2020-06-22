from grandchallenge.core.sitemaps import SubdomainSitemap
from grandchallenge.pages.models import Page


class PagesSitemap(SubdomainSitemap):
    priority = 0.8

    def items(self):
        return Page.objects.filter(
            permission_level=Page.ALL, challenge__hidden=False, hidden=False,
        )
