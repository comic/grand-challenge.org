from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.sitemaps import SubdomainSitemap


class AlgorithmsSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Algorithm.objects.filter(public=True)

    def lastmod(self, item: Algorithm):
        return item.modified
