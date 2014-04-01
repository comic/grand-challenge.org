from django.core.urlresolvers import resolve,Resolver404
from django.conf import settings

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
         
        try:           
            request = self.add_project_name(request)                        
        except Resolver404:            
            request.projectname = settings.MAIN_PROJECT_NAME
        
        try:
            request = self.add_project_pk(request)
        except Resolver404:
            request.project_pk = -1
         
        
        
        
    def add_project_name(self,request):
        """ Tries to infer the name of the project this project is regarding        
        
        Raises Resolver404
        
        TODO: Geting current project from the name given to it in urls.py is
              stinky. How to do this so that changing urls will not break this?
                
        """
        
        resolution = resolve(request.path)
        
        if resolution.kwargs.has_key("site_short_name"):
            projectname = resolution.kwargs["site_short_name"]
        elif resolution.kwargs.has_key("project_name"):
            projectname = resolution.kwargs["project_name"]
        else:
            projectname = settings.MAIN_PROJECT_NAME
        
        request.projectname = projectname
        
        
        return request

    def add_project_pk(self,request):
        """ Add unique key of current comicsite. This is used in admin views to
        auto fill comicsite for any comicsitemodel
        """
        
        request.project_pk = ComicSite.objects.get(short_name=request.projectname).pk
        return request
