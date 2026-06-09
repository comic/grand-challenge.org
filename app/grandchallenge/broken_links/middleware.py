import re

from django.conf import settings
from django.middleware.common import BrokenLinkEmailsMiddleware

from grandchallenge.broken_links.models import BrokenLink, IgnoredPattern


class BrokenLinkMiddleware(BrokenLinkEmailsMiddleware):
    def is_ignorable_request(self, request, uri, domain, referer):
        if super().is_ignorable_request(request, uri, domain, referer):
            return True

        patterns = IgnoredPattern.objects.values_list("pattern", flat=True)
        return any(re.search(pattern, uri) for pattern in patterns)

    def process_response(self, request, response):
        if response.status_code == 404 and not settings.DEBUG:
            domain = request.get_host()
            path = request.get_full_path()
            referer = request.headers.get("referer", "")

            if not self.is_ignorable_request(request, path, domain, referer):
                ua = request.headers.get("user-agent", "<none>")
                ip = request.META.get("REMOTE_ADDR", None)

                BrokenLink.objects.create(
                    domain=domain,
                    path=path,
                    referer=referer,
                    user_agent=ua,
                    ip_address=ip,
                    is_internal=self.is_internal_request(domain, referer),
                )

        return response
