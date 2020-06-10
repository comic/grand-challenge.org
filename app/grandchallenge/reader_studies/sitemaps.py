from grandchallenge.core.sitemaps import SubdomainSitemap
from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudiesSiteMap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return ReaderStudy.objects.filter(public=True)

    def lastmod(self, item: ReaderStudy):
        return item.modified
