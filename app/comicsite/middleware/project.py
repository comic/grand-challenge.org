from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404

from comicmodels.models import ComicSite


class ProjectMiddleware:
    """ Everything you do on comicframework is related to a project. This
    middleware makes this possible without having to duplicate 'project'
    variables everywhere. 
    
    """

    def process_request(self, request):
        """ Adds current project name to any request so it can be easily used
        in views.
                
        """
        request.projectname = self.get_challenge_name(request)

        try:
            request.challenge = ComicSite.objects.get(
                short_name=request.projectname
            )
            request.project_pk = request.challenge.pk
        except ComicSite.DoesNotExist:
            request.challenge = None
            request.project_pk = -1

    def get_challenge_name(self, request):
        """ Tries to infer the name of the project this project is regarding
        
        """
        try:
            resolution = resolve(request.path)
            if "challenge_short_name" in resolution.kwargs:
                projectname = resolution.kwargs["challenge_short_name"]
            else:
                projectname = settings.MAIN_PROJECT_NAME
        except Resolver404:
            projectname = settings.MAIN_PROJECT_NAME

        return projectname
