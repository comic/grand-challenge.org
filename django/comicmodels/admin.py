import pdb
from django import forms
from django.db import models
from django.contrib import admin

from guardian.admin import GuardedModelAdmin
from comicmodels.models import FileSystemDataset



class FileSystemDatasetForm(forms.ModelForm):
        
    folder = forms.CharField(widget=forms.TextInput)
    folder.required = False
    
    class Meta:
       
        model = FileSystemDataset
        

class FileSystemDatasetInitialForm(forms.ModelForm):
    """ In initial form, do not show folder edit field """                    
    class Meta:
        exclude = ['folder',]        
        model = FileSystemDataset        
        
class FileSystemDatasetAdmin(GuardedModelAdmin):    
    """ On initial creation, do not show the folder dialog because it is initialised to a default value"""
    
    def get_form(self, request, obj=None, **kwargs):        
        if obj:
            
            return FileSystemDatasetForm
        else:
            return FileSystemDatasetInitialForm 
            
     
            

    form = FileSystemDatasetForm
        


    
                    

admin.site.register(FileSystemDataset,FileSystemDatasetAdmin)

 