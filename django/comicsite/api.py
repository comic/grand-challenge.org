# The API class contains methods which can be called by javascript remote calls 
# to give additional information about a project in JSON format

import pdb
import json
from os import path
from django.http import HttpResponse,Http404,HttpResponseForbidden

from comicsite.views import get_data_folder_path,get_dirnames


def get_public_results(request,project_name):
        
    data_folder_path = get_data_folder_path(project_name)    
    public_results_path = path.join(data_folder_path,"results/public/")    
    
    try:
        dirnames = get_dirnames(public_results_path)
    except OSError:
        return HttpResponse("Cannot list public results. Public results should be in folder'results/public/' but this folder could not be found'")
    
    return HttpResponse(json.dumps(dirnames))
    