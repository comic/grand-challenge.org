from grandchallenge.core.sitemaps import SubdomainSitemap
from grandchallenge.products.models import Company, Product


class CompaniesSitemap(SubdomainSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Company.objects.all()


class ProductsSitemap(SubdomainSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Product.objects.all()
