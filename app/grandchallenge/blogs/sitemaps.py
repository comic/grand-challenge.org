from grandchallenge.blogs.models import Post
from grandchallenge.core.sitemaps import SubdomainSitemap


class PostsSitemap(SubdomainSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Post.objects.filter(published=True)

    def lastmod(self, item: Post):
        return item.modified
