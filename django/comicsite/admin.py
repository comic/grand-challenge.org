'''
Created on Jun 18, 2012

@author: Sjoerd
'''
import pdb
from django.contrib import admin
from django import forms
from django.db import models 
from django.contrib.auth.models import Group,Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.options import InlineModelAdmin
from django.forms import TextInput, Textarea
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user,assign

from comicmodels.models import ComicSite,Page


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
    
    # Make sure regular template overrides work. GuardedModelAdmin disables this
    # With change_form_template = None templates in templates/admin/comicsite/page
    # will be heeded again. 
    #change_form_template = None
    #Show these page params in admin overview list 
    list_display = ('title','comicsite','order')
    
    list_filter = ['comicsite']
    
    
    def save_model(self, request, obj, form, change):
        
        if obj.id is None:
            #at page creation, set the correct object permissions            
            # get admin group for the comicsite of this page                        
            agn = obj.comicsite.admin_group_name()            
            admingroup = Group.objects.get(name=agn)
                    
            # add change_page permission to the current page
            obj.save()                    
            assign("change_page",admingroup,obj)
                    
            # FIXME: is this double save really needed?        
            
        obj.save()
        move = form.cleaned_data['move']
        obj.move(move)
        
        permission_lvl = form.cleaned_data['permission_lvl']
        obj.setpermissions(permission_lvl)
    
    def queryset(self, request):
        """ overwrite this method to return only pages comicsites to which current user has access """                    
        user_qs = get_objects_for_user(request.user, 'comicmodels.change_page')
        return user_qs
    
    def response_change(self, request, obj, post_url_continue=None):
        """This makes the response after adding go to another apps changelist for some model"""        
        return HttpResponseRedirect(reverse("admin:comicmodels_comicsite_change",args=[obj.comicsite.pk]))



    def response_add(self, request, obj, post_url_continue=None):        
        return self.response_change(request, obj, post_url_continue=None)


    

class LinkedInline(InlineModelAdmin):
    """ Show some info and link to complete model admin
    Created to show all pages belonging to a site on site admin without having to edit pages
    there in a cramped interface 
    """
    template = 'admin/edit_inline/linked.html'
    
    admin_model_path = None    
    can_delete = False
        
    
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'40'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':20})},
    }
    
    


    def __init__(self, *args):
        super(LinkedInline, self).__init__(*args)
        if self.admin_model_path is None:
            self.admin_model_path = self.model.__name__.lower()
            
            



class PageInline(LinkedInline):
    model = Page
    extra = 0    
    
    fields = ('title','html_trunc','hidden','order')
    # make sure page is only displayed, not edited
    #readonly_fields=("title","html")
    readonly_fields=('title','html_trunc','hidden','order')
        
    
    def html_trunc(self,obj):
        return obj.html[:300]


class ComicSiteAdminForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={'rows':2, 'cols':80}),help_text = "Short summary of this project, max 1024 characters.")
    
    class Meta:
        model = ComicSite

class ComicSiteAdmin(GuardedModelAdmin):
    
    # Make sure regular template overrides work. GuardedModelAdmin disables this
    # With change_form_template = None templates in templates/admin/comicsite/page
    # will be heeded again.
    change_form_template = None
    
    form = ComicSiteAdminForm    
    inlines = [PageInline]
                    
    def queryset(self, request):
        """ overwrite this method to return only comicsites to which current user has access """
        qs = super(admin.ModelAdmin, self).queryset(request)

        if request.user.is_superuser:
            return qs
                
        user_qs = get_objects_for_user(request.user, 'comicmodels.change_comicsite')
        return user_qs
    
    
    def save_model(self, request, obj, form, change):        
        """ when saving for the first time, set object permissions; give all permissions to creator """
     
        if obj.id is None:      
            # create admins group            
            admingroup = Group.objects.create(name=obj.admin_group_name())
                        
            # create participants group                    
            participantsgroup = Group.objects.create(name=obj.short_name+"_participants")
            participantsgroup.save()
                                                        
            # add regular django class-level permissions so this group can use admin interface
            can_add = Permission.objects.get(codename="add_comicsite")
            can_change = Permission.objects.get(codename="change_comicsite")
            can_delete = Permission.objects.get(codename="delete_comicsite")
                                                
            can_add_page = Permission.objects.get(codename="add_page")
            can_change_page = Permission.objects.get(codename="change_page")
            can_delete_page = Permission.objects.get(codename="delete_page")
            
            admingroup.permissions.add(can_add,can_change,can_delete,can_add_page,
                                       can_change_page,can_delete_page)
            
            add_standard_permissions(admingroup,"filesystemdataset")
            
            # add object-level permission to the specific ComicSite so it shows up in admin    
            #admingroup.save()
            obj.save()
            #pdb.set_trace()
            assign("change_comicsite",admingroup,obj)
            
            # add current user to admins for this site 
            request.user.groups.add(admingroup)
        else:
            #if object already existed just save
            obj.save()

def add_standard_permissions(group,objname):
    """ Add delete_objname change_objname and add_objname to the given group"""  
    pdb.set_trace()
    can_add_obj = Permission.objects.get(codename="add_"+objname)
    can_change_obj = Permission.objects.get(codename="change_"+objname)
    can_delete_obj = Permission.objects.get(codename="delete_"+objname)
    group.permissions.add(can_add_obj,can_change_obj,can_delete_obj)
    
      

class PageAdminForm():
    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices=(
                         (models.BLANK_CHOICE_DASH[0]),
                         ('FIRST', 'First'),
                         ('UP', 'Up'),
                         ('DOWN', 'Down'),
                         ('LAST', 'Last'),
                        )
        
        


admin.site.register(ComicSite,ComicSiteAdmin)
admin.site.register(Page,PageAdmin)


    

    
