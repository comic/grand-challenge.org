import re

from django.contrib.sites.models import Site


def subdomain_middleware(get_response):
    def middleware(request):

        # Modify the request here
        host = request.get_host().lower()
        domain = Site.objects.get_current().domain.lower()

        pattern = f"^(?:(?P<subdomain>.*?)\.)?{domain}$"
        matches = re.match(pattern, host)

        if matches:
            request.subdomain = matches.group("subdomain")
        else:
            request.subdomain = None

        response = get_response(request)
        return response

    return middleware
