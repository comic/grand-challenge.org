import pdb
from django import forms
from django.db import models
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist

from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user
from comicmodels.models import FileSystemDataset,UploadModel





class ComicModelAdmin(GuardedModelAdmin):
    """Base class for ComicModel admin. Handles common functionality like setting permissions"""
    
    # if user has this permission, user can access this ComicModel.
    permission_name = 'view_ComicSiteModel'
    

    def save_model(self, request, obj, form, change):
        
        permission_lvl = form.cleaned_data['permission_lvl']
        obj.setpermissions(permission_lvl)
    
    def queryset(self, request): 
        """ overwrite this method to return only pages comicsites to which current user has access 
            
            note: GuardedModelAdmin can also restrict queryset to owned by user only, but this
            needs a 'user' field for each model, which I don't want because we use permission
            groups and do not restrict to user owned only.
        """
        try:
            user_qs = self.defaultQuerySet(request)
        except ObjectDoesNotExist as e:
            return UploadModel.objects.none()
        return user_qs
    
    def defaultQuerySet(self,request):
        """ Overwrite this method in child classes to make sure instance of that class is passed to 
            get_objects_for_users """ 
                
        
        return get_objects_for_user(request.user, self.permission_name,self)
    
    
    
    
    

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
    form = FileSystemDatasetForm
    
    def get_tag(self,obj):
        return obj.get_template_tag()
    
    def get_form(self, request, obj=None, **kwargs):        
        if obj:
            
            return FileSystemDatasetForm
        else:
            return FileSystemDatasetInitialForm
    
    def defaultQuerySet(self,request):
        """ Overwrite this method in child classes to make sure instance of that class is passed to 
            get_objects_for_users """ 
        
        return get_objects_for_user(request.user, self.permission_name,self)
                        
    
        
class UploadModelAdmin(ComicModelAdmin):

    list_display = ('title','file','comicsite')
    _default_manager = UploadModel.objects
    
                    

admin.site.register(FileSystemDataset,FileSystemDatasetAdmin)
admin.site.register(UploadModel,UploadModelAdmin)

    
    



 