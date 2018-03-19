from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404

from comicmodels.models import ComicSite, get_projectname


class ProjectMiddleware:
    """ Everything you do on comicframework is related to a project. This
    middleware makes this possible without having to duplicate 'project'
    variables everywhere. 
    
    """

    def process_request(self, request):
        """ Adds current project name to any request so it can be easily used
        in views.
                
        """
        request.is_projectadmin = self.is_projectadmin_url(request)
        request.projectname = self.get_project_name(request)
        request.project_pk = self.get_project_pk(request)

    def get_project_name(self, request):
        """ Tries to infer the name of the project this project is regarding
        
        """
        try:
            resolution = resolve(request.path)
            if "project_name" in resolution.kwargs:
                projectname = resolution.kwargs["project_name"]
            elif "challenge_short_name" in resolution.kwargs:
                projectname = resolution.kwargs["challenge_short_name"]
            elif request.is_projectadmin:
                projectname = get_projectname(resolution.namespace)
            else:
                projectname = settings.MAIN_PROJECT_NAME
        except Resolver404:
            projectname = settings.MAIN_PROJECT_NAME

        return projectname

    def get_project_pk(self, request):
        """ Get unique key of current comicsite. This is used in admin views to
        auto fill comicsite for any comicsitemodel
        """

        try:
            project_pk = ComicSite.objects.get(short_name=request.projectname).pk
        except ComicSite.DoesNotExist:
            project_pk = -1

        return project_pk

    def is_projectadmin_url(self, request):
        """ When you are in admin for a single project, only show objects for
            this project. This check must be made here as the request cannot
            be modified later
             
        """
        is_projectadmin = False
        try:
            resolution = resolve(request.path)
            # urls.py is set up in such a way that 'namespace' is always 'xxxadmin'
            # for example it is 'vesse12admin' for the vessel12 admin. It is only
            # 'admin' for the main (root) admin site. 
            is_projectadmin = resolution.namespace != 'admin' and self.is_admin_page(resolution)
        except Resolver404:
            is_projectadmin = False

        return is_projectadmin

    def is_admin_page(self, resolution):
        return resolution.app_name == 'admin'
