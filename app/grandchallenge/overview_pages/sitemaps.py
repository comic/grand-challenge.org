from grandchallenge.core.sitemaps import SubdomainSitemap
from grandchallenge.overview_pages.models import OverviewPage


class OverviewPagesSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return OverviewPage.objects.all(published=True)

    def lastmod(self, item: OverviewPage):
        return item.modified
