'''
Created on Jun 18, 2012

@author: Sjoerd
'''
import pdb
from django.contrib import admin
from django import forms
from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.auth.models import Group,Permission,User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.db import models
from django.forms import TextInput, Textarea
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode

from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user,assign

from comicmodels.models import ComicSite,Page
from comicmodels.signals import new_admin,removed_admin

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
    change_form_template = None
    
    #Show these page params in admin overview list 
    list_display = ('title','comicsite','order')    
    list_filter = ['comicsite']    
    formfield_overrides = {     
        models.TextField: {'widget': Textarea(attrs={'rows':40, 'cols':80})},
    }
    
    
    
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
     
        # code below was completely pasted from django.contrib.admin.options I needed to make changes to the
        # default response at the end, which I could not do without copying                
            #return super(PageAdmin,self).response_change(request,obj)
        opts = obj._meta

        # Handle proxy models automatically created by .only() or .defer().
        # Refs #14529
        verbose_name = opts.verbose_name
        module_name = opts.module_name
        if obj._deferred:
            opts_ = opts.proxy_for_model._meta
            verbose_name = opts_.verbose_name
            module_name = opts_.module_name

        pk_value = obj._get_pk_val()

        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': force_unicode(verbose_name), 'obj': force_unicode(obj)}
        if "_continue" in request.POST:
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if "_popup" in request.REQUEST:
                return HttpResponseRedirect(request.path + "?_popup=1")
            else:
                return HttpResponseRedirect(request.path)
        elif "_saveasnew" in request.POST:
            msg = _('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': force_unicode(verbose_name), 'obj': obj}
            self.message_user(request, msg)
            return HttpResponseRedirect(reverse('admin:%s_%s_change' %
                                        (opts.app_label, module_name),
                                        args=(pk_value,),
                                        current_app=self.admin_site.name))
        elif "_addanother" in request.POST:
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(verbose_name)))
            return HttpResponseRedirect(reverse('admin:%s_%s_add' %
                                        (opts.app_label, module_name),
                                        current_app=self.admin_site.name))
        #========== elif added by Sjoerd ======== 
        elif "save_goto_page" in request.POST:
                        
            #comicsite.views.page site.short_name page.title
            return HttpResponseRedirect(reverse("comicsite.views.page",args=[obj.comicsite.short_name,obj.title]))
        #========== below edited by Sjoerd ========
        else:
            self.message_user(request, msg)
            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            
            if self.has_change_permission(request, None):
                
                post_url = reverse('admin:%s_%s_change' %
                                   (obj.comicsite._meta.app_label, obj.comicsite._meta.module_name),
                                   args = (obj.comicsite.pk,),
                                   current_app=self.admin_site.name)
            else:
                post_url = reverse('admin:index',
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(post_url)


    def response_add(self, request, obj, post_url_continue=None):        
        return self.response_change(request, obj, post_url_continue)


    

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

 


class ComicSiteManager(models.Manager):
    """ Some extra table-level methods for getting ComicSites from database"""
    def non_hidden(self):
        """ like all(), but only return ComicSites for which hidden=false"""
        return self.filter(hidden=False)

class ComicSiteAdmin(admin.ModelAdmin):
    
    # Make sure regular template overrides work. GuardedModelAdmin disables this
    # With change_form_template = None templates in templates/admin/comicsite/page
    # will be heeded again.
    change_form_template = None
    
    list_display = ('short_name','hidden')    
    #list_filter = ['comicsite']
    form = ComicSiteAdminForm
    inlines = [PageInline]
    
    readonly_fields = ("manage_admin_link",)
    
    
    admin_manage_template = \
        'admin/comicmodels/admin_manage.html'
    
    
    def manage_admin_link(self,instance):
        return "<a href=\"admins\">View, Add or Remove Administrators for this project</a>"    
    manage_admin_link.allow_tags=True #allow links 
    manage_admin_link.short_description="Admins"
    
                
    def queryset(self, request):
        """ overwrite this method to return only comicsites to which current user has access """
        qs = super(ComicSiteAdmin, self).queryset(request)

        if request.user.is_superuser:
            return qs
                
        user_qs = get_objects_for_user(request.user, 'comicmodels.change_comicsite')
        return user_qs
    
    def get_urls(self):
        """
        Extends standard admin model urls to manage admins and participants:
        """
        
        urls = super(ComicSiteAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        myurls = patterns('',
            url(r'^(?P<object_pk>.+)/admins/$',
                view=self.admin_site.admin_view(self.admin_add_view),
                name='%s_%s_admins' % info),
            #url(r'^(?P<object_pk>.+)/permissions/user-manage/(?P<user_id>\-?\d+)/$',
            #    view=self.admin_site.admin_view(
            #       self.obj_perms_manage_user_view),
            #    name='%s_%s_permissions_manage_user' % info),
            #url(r'^(?P<object_pk>.+)/permissions/group-manage/(?P<group_id>\-?\d+)/$',
            #    view=self.admin_site.admin_view(
            #        self.obj_perms_manage_group_view),
            #    name='%s_%s_permissions_manage_group' % info),
        )
        return myurls + urls


    def get_base_context(self, request, obj):
        """
        Returns context dictionary with common admin and object permissions
        related content.
        """
        context = {
            'adminform': {'model_admin': self},
            'object': obj,
            'app_label': self.model._meta.app_label,
            'opts': self.model._meta,
            'original': hasattr(obj, '__unicode__') and obj.__unicode__() or\
                str(obj),
            'has_change_permission': self.has_change_permission(request, obj),
            #'model_perms': get_perms_for_model(obj),
            'title': _("Object permissions"),
        }
        return context
    
    def admin_add_view(self, request, object_pk):
        """
        Show all users in admin_group for this comicsite, allow adding users
        """        
        comicsite = get_object_or_404(ComicSite,id=object_pk)
                
        admins = User.objects.filter(groups__name=comicsite.admin_group_name(), is_superuser=False)
        
        if request.method == 'POST' and 'submit_add_user' in request.POST:
            
            user_form = AdminManageForm(request.POST)            
            
            if user_form.is_valid():
                user = user_form.cleaned_data['user']                
                
                #add given user to admins group
                admingroup = Group.objects.get(name=comicsite.admin_group_name())
                
                # add current user to admins for this site 
                user.groups.add(admingroup)                
                messages.add_message(request, messages.SUCCESS, 'User "'+user.username+'"\
                                     is now an admin for '+ comicsite.short_name)
                
               
                #send signal to be picked up for example by email notifier
                new_admin.send(sender=self,adder=request.user,new_admin=user,comicsite=comicsite
                               ,site=get_current_site(request))
                
                
                
        elif request.method == 'POST' and 'submit_delete_user' in request.POST:
            
            user_form = AdminManageForm(request.POST)            
            
            if user_form.is_valid():
                
                #add given user to admins group
                admingroup = Group.objects.get(name=comicsite.admin_group_name())                
                usernames_to_remove = request.POST.getlist('admins')
                removed = []
                
                msg2 = ""
                for username in usernames_to_remove:
                    if username == request.user.username:
                        msg2 = "Did not remove "+ username +" because that's you."
                        
                    else:                           
                                    
                        user = User.objects.get(username=username)                                
                        user.groups.remove(admingroup)
                        removed.append(username)
                
                msg = "Removed users [" + ", ".join(removed) + "] from "+comicsite.short_name+\
                      "admin group. " + msg2
                messages.add_message(request, messages.SUCCESS, msg)
                                
                #send signal to be picked up for example by email notifier                
                removed_admin.send(sender=self,adder=request.user,removed_admin=user,comicsite=comicsite
                                   ,site=get_current_site(request))                
                
        
        
        else:
            user_form = AdminManageForm()
        
        # populate available admins. #FIXME: duplicate code with change_view.
        # how to fill this amdin list without explicit filling? 
        choices = tuple([(user.username,user.username) for user in admins])    
        user_form.fields['admins'].widget.choices = choices            

        context = self.get_base_context(request, comicsite)
        context['user_form'] = user_form
        context['test'] = "put someting relevant here"
        

        return render_to_response(self.admin_manage_template,
            context, RequestContext(request, current_app=self.admin_site.name))
    
    
    
    def save_model(self, request, obj, form, change):        
        """ when saving for the first time, set object permissions; give all permissions to creator """
     
        if obj.id is None:      
            # if saving for the first time, create admin and participants permissions groups that go along with
            # this comicsite
            
            admingroup = Group.objects.create(name=obj.admin_group_name())            
            participantsgroup = Group.objects.create(name=obj.short_name+"_participants")
                        
            # add object-level permission to the specific ComicSite so it shows up in admin                
            obj.save()            
            assign("change_comicsite",admingroup,obj)
            
            # add current user to admins for this site 
            request.user.groups.add(admingroup)
        else:
            #if object already existed just save
            obj.save()



class AdminManageForm(forms.Form):
    admins = forms.CharField(required=False,widget=forms.SelectMultiple,help_text = "All admins for this project")            

    user = forms.RegexField(required=False,label=_("Username"), max_length=30,
        regex=r'^[\w.@+-]+$',
        error_messages = {
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters."),
            'does_not_exist': _("This user does not exist")})
    
    def clean_user(self):
        """
        Returns ``User`` instance based on the given username.
        """
        username = self.cleaned_data['user']
        if username != "": #pass if no user is given
            try:
                user = User.objects.get(username=username)
                return user
            except User.DoesNotExist:
                raise forms.ValidationError(
                    self.fields['user'].error_messages['does_not_exist'])


def add_standard_permissions(group,objname):
    """ Add delete_objname change_objname and add_objname to the given group"""  
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


    

    
