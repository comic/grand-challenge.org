# The API class contains methods which can be called by javascript remote calls 
# to give additional information about a project in JSON format

import json
from os import path

from django.http import HttpResponse

from comicsite.views import get_data_folder_path, get_dirnames


def get_public_results(request,project_name):
    """ Return an array of strings respresenting all results that can be publically
    viewed.
    """
    try:
        public_results = get_public_results_by_project_name(project_name)
    except OSError:
        return HttpResponse("Cannot list public results. Public results should be in folder'results/public/' but this folder could not be found'")
    
    return json.dumps(public_results) 
        
        
    
def get_public_results_by_project_name(project_name):
    """ Made a separate method here to be able to also call this API function from
    within other parts of the code.
    
    raises OSError when no results folder can be found for this project
    """
        
    data_folder_path = get_data_folder_path(project_name)    
    public_results_path = path.join(data_folder_path,"results/public/")
    dirnames = get_dirnames(public_results_path)
        

    return dirnames
    