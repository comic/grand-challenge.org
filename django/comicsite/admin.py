'''
Created on Jun 18, 2012

@author: Sjoerd
'''
import logging
# ======================= testing creating of custom admin
# Almost same import as in django.contrib.admin
import re
from functools import update_wrapper

from django import forms
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.options import InlineModelAdmin
# NOTICE: that we are not importing site here!
# basically this is the only one import you'll need
# other imports required if you want easy replace standard admin package with yours
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission, User
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse, NoReverseMatch, clear_url_caches
from django.db import models
from django.forms import TextInput, Textarea
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import six
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from guardian.shortcuts import get_objects_for_user, assign_perm
from six.moves import reload_module

from comicmodels.admin import ComicModelAdmin, RegistrationRequestAdmin
from comicmodels.models import Page, RegistrationRequest
from comicmodels.signals import new_admin, removed_admin

logger = logging.getLogger("django")


def reload_url_conf():
    """ urlpatterns for project admin in urls.py are generated based on je current
    projects in the database. When a project gets added, the admin urls for the
    new project are not in the imported urls.py. A reload is required
    """    
    import comicsite.urls
    import comic.urls
    reload_module(comicsite.urls)
    reload_module(comic.urls)
    
    
def clear_url_resolver_cache():
    clear_url_caches()


def get_comicsite_shortnames_that_user_is_admin_for(user):
    """
    Returns a list of shortnames that the user is an administrator for
    :param user: The user
    :return: List of short comicsite names
    """
    user_admin_groups = User.objects.get(username=user).groups.all().filter(models.Q(name__endswith='_admins'))
    short_names = [x.name.rstrip('_admins') for x in user_admin_groups]
    return short_names

def filter_if_not_empty(qs, filter_set):
    """
    Utility function that filters a query set by the given list of Q functions. Returns nothing if the list is empty
    :param qs: The query set
    :param filter_set: The list of q functions
    :return: A filtered queryset
    """
    if len(filter_set) == 0:
        return qs.none()
    else:
        return qs.filter(filter_set)

def filter_projects_by_user_admin(qs, user):
    """
    Filters a queryset of projects by user admin status
    :param qs: A queryset containing projects (comicsites)
    :param user: The User
    :return: The comicsites this user is a admin for
    """
    admin_projects = models.Q()

    for s in get_comicsite_shortnames_that_user_is_admin_for(user):
        admin_projects |= models.Q(short_name=s)

    return filter_if_not_empty(qs, admin_projects)

def filter_pages_by_user_admin(qs, user):
    """
    Filters a queryset of pages by the user admin status
    :param qs: A queryset containg pages
    :param user: The user
    :return: The pages this user can edit
    """
    admin_projects = models.Q()

    for s in get_comicsite_shortnames_that_user_is_admin_for(user):
        admin_projects |= models.Q(comicsite__short_name=s)

    return filter_if_not_empty(qs, admin_projects)

class ProjectAdminSite2(AdminSite):
    """Admin for a specific project. Only shows and allows access to object
    associated with that project"""


    def __init__(self, project, name='admin', app_name='admin'):
        super(ProjectAdminSite2, self).__init__(name,app_name)
        self.project = project

    def get_urls(self):
                
        for model, model_admin in six.iteritems(self._registry):
            
            # Wrap all modeladmin queryset methods so that they only return content
            # relevant for the current project
            model_admin.get_queryset = self.queryset_wrapper(model_admin.get_queryset)
            
            model_admin.add_view = self.add_view_wrapper(model_admin.add_view)
            

        return super(ProjectAdminSite2, self).get_urls()
    
    def register_comicmodels(self):
        """ Make sure all relevant models can be edited and are shown in this projectadminsite 
        
        """
        self.register(ComicSite, ComicSiteAdmin)
        self.register(Page, PageAdmin)
        self.register(RegistrationRequest, RegistrationRequestAdmin)


    def queryset_wrapper(self, querysetfunction):
        """ Modify queryset so it only show objects related to the current project
        """
        def wrap(*args, **kwargs):
            
            qs = querysetfunction(*args, **kwargs)
            # Hack because registrationrequest does not have a 'comicsite' param,
            # but rather a 'project' param with the same function. There is no good
            # reason for this, but is is like this.. Changing this
            # Is rather a lot work because of dependencies with the database and
            # other code. Going for quick fix here. Ideal solution is to rewrite
            # all comic objects to have a 'project' param.
                        
            if qs:
                if hasattr(qs[0],'project'):
                    qs = qs.filter(project=self.project)
                elif hasattr(qs[0],'comicsite'):
                    qs = qs.filter(comicsite=self.project)
                else:
                    pass
            
            if qs:
                # in case this IS a project instead of a project related object
                # just show this project
                if type(qs[0]) == ComicSite:
                    qs = qs.filter(short_name=self.project.short_name)

            return qs

        return wrap


    def add_view_wrapper(self, add_view):
        """ In projectadmin you can only create objects for this project. That
        why you should not have a field to choose this, and 'project' or 'comicsite'
        field is filled automatically here
        """
        def wrap(request,*args, **kwargs):
            
            if request.method == 'POST':
                if "comicsite" in request.POST:
                    request.POST["comicsite"] = self.project.pk
                
                if "project" in request.POST:
                    request.POST["project"] = self.project.pk
                    
            return add_view(request,*args,**kwargs)
            
        return wrap
    
    def admin_view(self, view, cacheable=False):
        """
        Changes to original admin view: this one passes kwargs to the view as 'extra_context'. This way the
        url argument site_short_name gets passed to all the admin functions so they can do project specific
        stuff.
        """
        def inner(request, *args, **kwargs):
            
            # Let templates know this is projectadmin, and which project it is
            extra_context = {"projectadmin":True,
                             "project_name":self.project.short_name,
                             "project_pk":self.project.pk}
            
            # If there is existing extra_context, add this. but then remove it
            # from kwargs because otherwise you will get a "got two values for" exception
            if "extra_context" in kwargs:
                kwargs["extra_context"].update(extra_context)
            else:
                kwargs["extra_context"] = extra_context
            
            # certain standard admin urls cannot handle the extra_context var,
            # making an excpetion here
            no_extra_context = ["jsi18n","view_on_site","logout","password_change",
                                "password_change_done"]
            if request.resolver_match.url_name in no_extra_context:
                del kwargs["extra_context"]
            
            
            # Going for high ranking here in most unreadable line of python 2014
            # What would uncle bob say? Would he even survive? And how could Guido's
            # dream of clean readble code have turned so nightmarish? 
            return super(ProjectAdminSite2,self).admin_view(view)(request,
                                                                  *args,
                                                                  **kwargs)

        return update_wrapper(inner, view)
    
    @never_cache
    def index(self, request, extra_context=None):
        """Show the edit page of the current project. This is the main source of information for any project so
           this should be shown by default, instead of list of all objects"""

        if extra_context is None:
            extra_context = {}

        comicsiteadmin = self._registry[ComicSite]
        extra_context["projectname"] = request.projectname
        return comicsiteadmin.change_view(request, str(self.project.pk), "", extra_context)
    
    def has_permission(self,request):
        """ For projectadmin, in addition to standard django checks, check if requesting
        user is an admin for this project    
        """
        standard_check = super(ProjectAdminSite2,self).has_permission(request)        
        return standard_check and self.project.is_admin(request.user)
    

from comicmodels.models import ComicSite

class AllProjectAdminSites(object):
    """ Class to use in urls.py, will build explicit urls and projectadmins for 
    every project which has been defined in database
    """
        
    

    @property
    def allurls(self):
                
        pat = []
        for project in ComicSite.objects.all():
            pat += self.get_admin_patterns(project)
                #return url(r'^admin/', include(projectadminsite.urls)),
        return pat
    
    
    def get_admin_patterns(self,project):
        """ get all url patterns for project, to use in urls.py
        
        """
        name = project.get_project_admin_instance_name()
        projectadminsite = ProjectAdminSite2(name=name,project=project)
        projectadminsite.register_comicmodels()
        
        urls = projectadminsite.get_urls()
        regex = r'^{}/admin/'.format(project.short_name.lower())
        
        urlpatterns = patterns('',
                               url(regex,
                               projectadminsite.urls)
                               )
        return urlpatterns


class PageAdminForm(forms.ModelForm):
    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
                         (models.BLANK_CHOICE_DASH[0]),
                         ('FIRST', 'First'),
                         ('UP', 'Up'),
                         ('DOWN', 'Down'),
                         ('LAST', 'Last'),
                        )

    class Meta:
        model = Page
        fields = '__all__'

class PageAdmin(ComicModelAdmin):
    """Define the admin interface for pages"""

    form = PageAdminForm

    # Make sure regular template overrides work. GuardedModelAdmin disables this
    # With change_form_template = None templates in templates/admin/comicsite/page
    # will be heeded again.
    change_form_template = None

    # Show these page params in admin overview list
    list_display = ('title', 'comicsite', 'order')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':40, 'cols':80})},
    }


    def save_model(self, request, obj, form, change):

        if obj.id is None:
            self.first_save(obj)

        obj.save()
        move = form.cleaned_data['move']
        obj.move(move)

        permission_lvl = form.cleaned_data['permission_lvl']
        obj.setpermissions(permission_lvl)

    def first_save(self, obj):
        # at page creation, set the correct object permissions
        # get admin group for the comicsite of this page
        agn = obj.comicsite.admin_group_name()
        admingroup = Group.objects.get(name=agn)
        # add change_page permission to the current page
        obj.save()
        assign_perm("change_page", admingroup, obj)


    def get_queryset(self, request):
        """ overwrite this method to return only pages comicsites to which current user has access
            In Addition, if your are on a project-admin page, show only content associated with that
            project
        """

        qs = get_objects_for_user(request.user, 'comicmodels.change_page')
        if request.user.is_superuser:
            return qs
        else:
            qs = filter_pages_by_user_admin(qs, request.user)

        if request.is_projectadmin:  # this info is added by project middleware
            qs = qs.filter(comicsite__short_name=request.projectname)

        return qs

    def response_change(self, request, obj, post_url_continue=None):
        """This makes the response after adding go to another apps changelist for some model"""

        # code below was completely pasted from django.contrib.admin.options I needed to make changes to the
        # default response at the end, which I could not do without copying
            # return super(PageAdmin,self).response_change(request,obj)
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
            # comicsite.views.page site.short_name page.title
            return HttpResponseRedirect(reverse("comicsite.views.page", args=[obj.comicsite.short_name, obj.title]))

        #========== below edited by Sjoerd ========
        else:
            self.message_user(request, msg)
            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.

            if self.has_change_permission(request, None):

                post_url = reverse('admin:%s_%s_change' %
                                   (obj.comicsite._meta.app_label, obj.comicsite._meta.module_name),
                                   args=(obj.comicsite.pk,),
                                   current_app=self.admin_site.name)
            else:
                post_url = reverse('admin:index',
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(post_url)


    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """So I have a jquery WYSIWYG editor (ckedit) on the page source (field Html). This editor can also do
           'upload image' and I want the upload to go to a different folder based on the comicsite you are editing.
           This proved esceedingly and exasperatingly difficult.
           Solution now: just add the comicsite as attribute to each **** field.widget in the form. if possible
           TODO: can this be different? This solution makes me cry but I see no other at the moment.
           """

        # find out in which project you are currently working/
        if hasattr(obj, "comicsite"):
            # editing a page, get comicsite from the object you're editing
            site_short_name = obj.comicsite.short_name

        elif request.GET.has_key("comicsite"):
            # you're starting a new page, obj does not exist. Get comicsite from url parameter which is passed for new pages
            site_short_name = ComicSite.objects.get(pk=request.GET["comicsite"]).short_name
        else:
            # try to get current project by url TODO: This solution is too specific for page. Should be  a general
            # property of the admin site. But I can't get this right at projectadmin.

            match = re.match(r"^/site/(?P<site_short_name>[\w-]+)/admin/.*", request.path)
            if match:
                site_short_name = match.group("site_short_name")
            else:
                raise KeyError("Cannot determine to which project this page belongs. I don't know where to upload images which might be uploaded.")

        # if current project was found, set appropriate things in the form:
        # make sure ckedit knows where to upload if upload in editor is used

        fields = context['adminform'].form.fields
        if 'html' in fields:
            fields['html'].widget.config['comicsite'] = site_short_name


        template_response = super(ComicModelAdmin, self).render_change_form(request, context, add, change, form_url, obj)
        return template_response




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

    fields = ('title', 'html_trunc', 'link', 'hidden', 'order')
    # make sure page is only displayed, not edited
    # readonly_fields=("title","html")
    readonly_fields = ('title', 'html_trunc', 'link', 'hidden', 'order')

    def html_trunc(self, obj):
        return obj.html[:300]

    def link(self, obj):
        # def page(request, site_short_name, page_title):
        """ Link to page directly so you can view it as regular user"""
        link_url = reverse('comicsite.views.page', kwargs={"site_short_name":obj.comicsite.short_name, "page_title":obj.title})
        link_text = "view " + obj.title
        link_html = "<a href=\"" + link_url + "\">" + link_text + "</a>"

        return link_html
    link.allow_tags = True

class ComicSiteAdminForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs=
                                                        {'rows':4, 'cols':80}),
                                 help_text="Short summary of this project,"
                                 " max 1024 characters.")
    disclaimer = forms.CharField(required=False,
                                 widget=forms.Textarea(attrs=
                                                       {'rows':4, 'cols':120}),
                                 help_text="'Under construction'-like "
                                 "banner to show on each page")

    short_name = forms.CharField(required=False,
                                 widget=forms.TextInput(attrs=
                                                       {'size':30, })
                           )

    class Meta:
        model = ComicSite
        fields = '__all__'




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

    # make all textboxes wider because having them too small is stupid
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'100%'})}, }

    list_display = ('short_name', 'link', 'hidden')
    # list_filter = ['comicsite']
    form = ComicSiteAdminForm
    inlines = [PageInline]

    fieldsets = (
        (None, {
                'fields': ('short_name', 'description', 'logo')
        }),
        ('Layout', {
                'classes': ('collapse',),
                'fields': ('header_image', 'skin', 'disclaimer')
                }),
        ('Metadata', {
                'classes': ('collapse',),
                'fields': ('workshop_date', 'event_name', 'event_url',
                           'is_open_for_submissions', 'submission_page_name', 'number_of_submissions', 'last_submission_date',
                           'offers_data_download', 'number_of_downloads',
                           'publication_url', 'publication_journal_name'
                           )
                }),
        ('Users', {
                'classes': ('collapse',),
                'fields': ('manage_admin_link', 'manage_participation_request_link', 'require_participant_review')
            }),
        ('Advanced options', {
                'classes': ('collapse',),
                'fields': ('hidden', 'hide_signin', 'hide_footer')
            }),

    )
    readonly_fields = ("manage_admin_link", "link", "manage_participation_request_link")

    admin_manage_template = \
        'admin/comicmodels/admin_manage.html'



    def link(self, obj):
        """ link to current project, so you can easily view project """
        try:
            link_url = reverse('comicsite.views.site', args=[obj.short_name])
            link_text = "view " + obj.short_name
            link_html = "<a href=\"" + link_url + "\">" + link_text + "</a>"

        except NoReverseMatch as e:
            #
            logger.error(e)
            return ""

        return link_html
    link.allow_tags = True


    def manage_admin_link(self, instance):
        """ HTML link to the overview of all admins for this project. Used in 
        admin interface. 
        """
        
        url = reverse("admin:comicmodels_comicsite_admins",args=[instance.pk],current_app=instance.get_project_admin_instance_name())
        return "<a href={}>View, Add or Remove Administrators for this project</a>".format(url)
    
    manage_admin_link.allow_tags = True  # allow links
    manage_admin_link.short_description = "Admins"

    def manage_participation_request_link(self, instance):
        """ HTML link to overview of all participation requests. Used in admin.
        """
        
        url = reverse("admin:comicmodels_registrationrequest_changelist",current_app=instance.get_project_admin_instance_name())        
        return "<a href=\'{}'>Approve or reject participation requests</a>".format(url)

    manage_participation_request_link.allow_tags = True  # allow links
    manage_participation_request_link.short_description = "Participation Requests"


    def get_queryset(self, request):
        """ overwrite this method to return only comicsites to which current user has access """
        qs = super(ComicSiteAdmin, self).get_queryset(request)

        if request.user.is_superuser:
            return qs
        else:
            qs = get_objects_for_user(request.user, 'comicmodels.change_comicsite')
            qs = filter_projects_by_user_admin(qs, request.user)
            return qs

    def get_urls(self):
        """
        Extends standard admin model urls to manage admins and participants:
        """

        urls = super(ComicSiteAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = patterns('',
            url(r'^(?P<object_pk>.+)/admins/$',
                view=self.admin_site.admin_view(self.admin_add_view),
                name='%s_%s_admins' % info),
            url(r'^(?P<object_pk>.+)/registration_requests/$',
                view=self.admin_site.admin_view(self.registration_requests_view),
                name='%s_%s_participantrequests' % info),
            # url(r'^(?P<object_pk>.+)/permissions/user-manage/(?P<user_id>\-?\d+)/$',
            #    view=self.admin_site.admin_view(
            #       self.obj_perms_manage_user_view),
            #    name='%s_%s_permissions_manage_user' % info),
            # url(r'^(?P<object_pk>.+)/permissions/group-manage/(?P<group_id>\-?\d+)/$',
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
            # 'model_perms': get_perms_for_model(obj),
            'title': _("Object permissions"),
        }
        return context


    def admin_add_view(self, request, object_pk, extra_context=None):
        """
        Show all users in admin_group for this comicsite, allow adding users
        """

        if extra_context is None:
            extra_context = {}

        comicsite = get_object_or_404(ComicSite, id=object_pk)
        admins = User.objects.filter(groups__name=comicsite.admin_group_name())


        if request.method == 'POST' and 'submit_add_user' in request.POST:
            user_form = AdminManageForm(request.POST)
            if user_form.is_valid():
                user = user_form.cleaned_data['user']
                # add given user to admins group
                admingroup = Group.objects.get(name=comicsite.admin_group_name())
                # add current user to admins for this site
                user.groups.add(admingroup)
                messages.add_message(request, messages.SUCCESS, 'User "' + user.username + '"\
                                     is now an admin for ' + comicsite.short_name)

                # send signal to be picked up for example by email notifier
                new_admin.send(sender=self, adder=request.user, new_admin=user, comicsite=comicsite
                               , site=get_current_site(request))



        elif request.method == 'POST' and 'submit_delete_user' in request.POST:
            user_form = AdminManageForm(request.POST)

            if user_form.is_valid():

                # add given user to admins group
                admingroup = Group.objects.get(name=comicsite.admin_group_name())
                usernames_to_remove = request.POST.getlist('admins')
                removed = []

                msg2 = ""
                for username in usernames_to_remove:
                    if username == request.user.username:
                        msg2 = "Did not remove " + username + " because that's you."

                    else:

                        user = User.objects.get(username=username)
                        user.groups.remove(admingroup)
                        removed.append(username)

                        # send signal to be picked up for example by email notifier
                        removed_admin.send(sender=self, adder=request.user, removed_admin=user, comicsite=comicsite,
                                           site=get_current_site(request))

                msg = "Removed users [" + ", ".join(removed) + "] from " + comicsite.short_name + \
                      " admin group. " + msg2
                messages.add_message(request, messages.SUCCESS, msg)

        else:
            user_form = AdminManageForm()

        # populate available admins. #FIXME: duplicate code with change_view.
        # how to fill this amdin list without explicit filling?
        choices = tuple([(user.username, user.username) for user in admins])
        user_form.fields['admins'].widget.choices = choices

        context = self.get_base_context(request, comicsite)
        context['user_form'] = user_form
        context['title'] = "Manage Admins"

        context.update(extra_context)

        return render_to_response(self.admin_manage_template,
            context, RequestContext(request, current_app=self.admin_site.name))


    def save_model(self, request, obj, form, change):
        """ when saving for the first time, set object permissions; give all permissions to creator """

        if obj.id is None:
            self.set_base_permissions(request, obj)
            reload_url_conf()
            clear_url_resolver_cache()
            


        else:
            # if object already existed just save
            obj.save()
            
    
    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        self.remove_related_groups(request,obj)
        obj.delete()

    def remove_related_groups(self,request,obj):
        Group.objects.get(name=obj.admin_group_name()).delete()
        Group.objects.get(name=obj.participants_group_name()).delete()

    def set_base_permissions(self, request, obj):
        """ if saving for the first time, create admin and participants permissions groups that go along with
        this comicsite

        """
        admingroup = Group.objects.create(name=obj.admin_group_name())
        participantsgroup = Group.objects.create(name=obj.participants_group_name())

        # add object-level permission to the specific ComicSite so it shows up in admin
        obj.save()
        assign_perm("change_comicsite", admingroup, obj)
        # add all permissions for pages, comicsites and filesystem dataset so these can be edited by admin group
        add_standard_permissions(admingroup, "comicsite")
        add_standard_permissions(admingroup, "page")
        add_standard_permissions(admingroup, "filesystemdataset")

        # add current user to admins for this site
        request.user.groups.add(admingroup)


    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """ overwrite this to inject some useful info message at first creation """
        if obj is None:
            messages.info(request, 'Please fill out the form to create a new project. <b>Required fields are bold.</b> Please save your project before adding pages or admins.', extra_tags='safe')

        return super(ComicSiteAdmin, self).render_change_form(request, context, add, change, form_url, obj)


    def registration_requests_view(self, request, object_pk):
        """ Used to view requests to participate in admin interface
        """

        comicsite = get_object_or_404(ComicSite, id=object_pk)
        admins = User.objects.filter(groups__name=comicsite.admin_group_name(), is_superuser=False)

        context = self.get_base_context(request, comicsite)

        from comicmodels.admin import RegistrationRequestAdmin
        from comicmodels.models import RegistrationRequest

        rra = RegistrationRequestAdmin(RegistrationRequest, admin.site)
        return rra.changelist_view(request)
        # TODO: why is RegistrationRequestAdmin in a different class. This is
        # so confusing. Think about class responsibilities and fix this.


        # return render_to_response(self.admin_manage_template,
        #    context, RequestContext(request, current_app=self.admin_site.name))


class AdminManageForm(forms.Form):
    admins = forms.CharField(required=False, widget=forms.SelectMultiple, help_text="All admins for this project")
    user = forms.ModelChoiceField(queryset=User.objects.all(), empty_label="<user to add>", required=False)


def add_standard_permissions(group, objname):
    """ Add delete_objname change_objname and add_objname to the given group"""
    can_add_obj = Permission.objects.get(codename="add_" + objname)
    can_change_obj = Permission.objects.get(codename="change_" + objname)
    can_delete_obj = Permission.objects.get(codename="delete_" + objname)
    group.permissions.add(can_add_obj, can_change_obj, can_delete_obj)

# this variable is included in urls.py to get admin urls for each project in
# the database  
projectadminurls = AllProjectAdminSites()

admin.site.register(ComicSite, ComicSiteAdmin)
admin.site.register(Page, PageAdmin)

