from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin

from grandchallenge.challenges.models import Challenge


class ProjectMiddleware(MiddlewareMixin):
    """ Everything you do on comicframework is related to a challenge. This
    middleware makes this possible without having to duplicate 'challenge'
    variables everywhere. 
    
    """

    def process_request(self, request):
        """ Adds current project name to any request so it can be easily used
        in views.
                
        """
        try:
            request.challenge = Challenge.objects.get(
                short_name=self.get_challenge_name(request)
            )
        except Challenge.DoesNotExist:
            request.challenge = None

    def get_challenge_name(self, request):
        """ Tries to infer the name of the project this project is regarding

        """
        try:
            resolution = resolve(request.path)
            if "challenge_short_name" in resolution.kwargs:
                name = resolution.kwargs["challenge_short_name"]
            else:
                name = settings.MAIN_PROJECT_NAME
        except Resolver404:
            name = settings.MAIN_PROJECT_NAME
        return name
