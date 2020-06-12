from grandchallenge.core.sitemaps import SubdomainSitemap
from grandchallenge.policies.models import Policy


class PoliciesSitemap(SubdomainSitemap):
    changefreq = "monthly"

    def items(self):
        return Policy.objects.all()
