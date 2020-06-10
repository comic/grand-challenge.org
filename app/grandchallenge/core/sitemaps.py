from django.contrib.flatpages.models import FlatPage
from django.contrib.sitemaps import Sitemap

from grandchallenge.subdomains.utils import reverse


class SubdomainSitemap(Sitemap):
    def _urls(self, page, protocol, domain):
        urls = super()._urls(page, protocol, domain)

        # Remove the automatically added location as this is added by our
        # subdomain reversal
        for url in urls:
            url["location"] = url["location"].replace(
                f"{protocol}://{domain}{protocol}://", f"{protocol}://"
            )

        return urls


class CoreSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return [
            "home",
            "archives:list",
            "reader-studies:list",
            "challenges:list",
            "algorithms:list",
            "products:product-list",
        ]

    def location(self, item):
        return reverse(item)


class FlatPagesSitemap(SubdomainSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return FlatPage.objects.all()
