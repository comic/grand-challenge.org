from django.utils.deprecation import MiddlewareMixin


class SubdomainMiddleware(MiddlewareMixin):
    """ Add subdomain to any request. Thanks to Dave Fowler. 
    http://thingsilearned.com/2009/01/05/using-subdomains-in-django/
    """

    def process_request(self, request):
        """Parse out the subdomain from the request"""
        request.subdomain = None
        host = request.META.get('HTTP_HOST', '')
        host_s = host.replace('www.', '').split('.')
        if len(host_s) > 2:
            request.subdomain = '.'.join(host_s[:-2])
