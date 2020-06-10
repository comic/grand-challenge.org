from grandchallenge.challenges.models import Challenge
from grandchallenge.core.sitemaps import SubdomainSitemap


class ChallengesSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Challenge.objects.filter(hidden=False)

    def lastmod(self, item: Challenge):
        return item.modified
