import pdb
from django import forms
from django.db import models
from django.contrib import admin

from guardian.admin import GuardedModelAdmin
from comicmodels.models import FileSystemDataset,UploadModel



class FileSystemDatasetForm(forms.ModelForm):
                
    folder = forms.CharField(widget=forms.TextInput(attrs={'size': 60}),help_text = "All files for this dataset are stored in this folder on disk")
    folder.required = False    
    
    #TODO: print {% tag %} values in this
    tag = forms.CharField(widget=forms.TextInput(attrs={'size': 60, 'readonly':'readonly'}),help_text = "To show all files in this dataset as downloads on a page, copy-paste this tag into the page contents")
    
    def __init__(self, *args, **kwargs):
        # only change attributes if an instance is passed
                    
        instance = kwargs.get('instance')
        #pdb.set_trace()
        if instance:
            self.base_fields['tag'].initial = instance.get_template_tag()
        
            #self.base_fields['calculated'].initial = (instance.bar == 42)
        forms.ModelForm.__init__(self, *args, **kwargs)

    
    class Meta:       
       model = FileSystemDataset
       
        

class FileSystemDatasetInitialForm(forms.ModelForm):
    """ In initial form, do not show folder edit field """                    
    class Meta:
        exclude = ['folder',]        
        model = FileSystemDataset        


class FileSystemDatasetAdmin(GuardedModelAdmin):    
    """ On initial creation, do not show the folder dialog because it is initialized to a default value"""
        
    list_display = ('title','description','get_tag','comicsite')
    
    def get_tag(self,obj):
        return obj.get_template_tag()
    
    def get_form(self, request, obj=None, **kwargs):        
        if obj:
            
            return FileSystemDatasetForm
        else:
            return FileSystemDatasetInitialForm 
            
     
            

    form = FileSystemDatasetForm
        
class UploadModelAdmin(GuardedModelAdmin):    
    """ On initial creation, do not show the folder dialog because it is initialized to a default value"""
        
    list_display = ('title','file','comicsite')
                    

admin.site.register(FileSystemDataset,FileSystemDatasetAdmin)
admin.site.register(UploadModel,UploadModelAdmin)

 