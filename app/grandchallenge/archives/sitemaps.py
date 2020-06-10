from grandchallenge.archives.models import Archive
from grandchallenge.core.sitemaps import SubdomainSitemap


class ArchivesSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Archive.objects.filter(public=True)

    def lastmod(self, item: Archive):
        return item.modified
