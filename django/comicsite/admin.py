'''
Created on Jun 18, 2012

@author: Sjoerd
'''

from django.contrib import admin
from django import forms
from django.db import models 
from django.contrib.auth.models import Group


from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user
from models import ComicSite,Page
import pdb



class PageAdminForm(forms.ModelForm):
    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices=(
                         (models.BLANK_CHOICE_DASH[0]),
                         ('FIRST', 'First'),
                         ('UP', 'Up'),
                         ('DOWN', 'Down'),
                         ('LAST', 'Last'),
                        )
    class Meta:
        model = Page

class PageAdmin(GuardedModelAdmin):
    """Define the admin interface for pages"""
    form = PageAdminForm
    
    def save_model(self, request, obj, form, change):
        obj.save()
        move = form.cleaned_data['move']
        obj.move(move)
    
    #Show these page params in admin overview list 
    list_display = ('title','ComicSite','order')
    


class ComicSiteAdmin(GuardedModelAdmin):
    
    def __init__(self,*args,**kwargs):
        super(ComicSiteAdmin, self).__init__(*args, **kwargs)  
        self.user_can_access_owned_objects_only = True
    
    def queryset(self, request):
        """ overwrite this method to return only comicsites to which current user has access """
        qs = super(admin.ModelAdmin, self).queryset(request)

        if request.user.is_superuser:
            return qs
                
        user_qs = get_objects_for_user(request.user, 'comicsite.change_comicsite')
        return user_qs
    
    def save_model(self, request, obj, form, change):        
        """ when saving for the first time, set object permissions; give all permissions to creator """
        pdb.set_trace()
        if obj.id is not None:      
            # create admins group
            group = Group.objects.create(name=self.short_name+"Admin")
            pdb.set_trace()
            # create participants group
            
            
            # give all this sites permissions to admin group  
            
            # add current user to admins group
            
            
            max_order = Page.objects.filter(ComicSite__pk=self.ComicSite.pk).aggregate(Max('order'))                
            self.order = max_order["order__max"] + 1
    
        obj.save()
        
    
        

admin.site.register(ComicSite,ComicSiteAdmin)
admin.site.register(Page,PageAdmin)


    

    
