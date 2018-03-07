import logging
# ======================= testing creating of custom admin
# Almost same import as in django.contrib.admin
from functools import update_wrapper

from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.contrib import messages
# NOTICE: that we are not importing site here!
# basically this is the only one import you'll need
# other imports required if you want easy replace standard admin package with yours
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.forms import TextInput
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import six
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from guardian.shortcuts import get_objects_for_user

from comicmodels.signals import new_admin, removed_admin

logger = logging.getLogger("django")


def get_comicsite_shortnames_that_user_is_admin_for(user):
    """
    Returns a list of shortnames that the user is an administrator for
    :param user: The user
    :return: List of short comicsite names
    """
    User = get_user_model()
    user_admin_groups = User.objects.get(username=user).groups.all().filter(
        models.Q(name__endswith='_admins'))
    # Strip _admins from string
    short_names = [x.name[:-7] for x in user_admin_groups]
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


class ProjectAdminSite2(AdminSite):
    """Admin for a specific project. Only shows and allows access to object
    associated with that project"""

    def __init__(self, project, name='admin'):
        super(ProjectAdminSite2, self).__init__(name)
        self.project = project

    def get_urls(self):

        for model, model_admin in six.iteritems(self._registry):
            # Wrap all modeladmin queryset methods so that they only return content
            # relevant for the current project
            model_admin.get_queryset = self.queryset_wrapper(
                model_admin.get_queryset)

            model_admin.add_view = self.add_view_wrapper(model_admin.add_view)

        return super(ProjectAdminSite2, self).get_urls()

    def register_comicmodels(self):
        """ Make sure all relevant models can be edited and are shown in this projectadminsite 
        
        """
        self.register(ComicSite, ComicSiteAdmin)

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
                if hasattr(qs[0], 'project'):
                    qs = qs.filter(project=self.project)
                elif hasattr(qs[0], 'comicsite'):
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

        def wrap(request, *args, **kwargs):

            if request.method == 'POST':
                if "comicsite" in request.POST:
                    request.POST["comicsite"] = self.project.pk

                if "project" in request.POST:
                    request.POST["project"] = self.project.pk

            return add_view(request, *args, **kwargs)

        return wrap

    def admin_view(self, view, cacheable=False):
        """
        Changes to original admin view: this one passes kwargs to the view as 'extra_context'. This way the
        url argument site_short_name gets passed to all the admin functions so they can do project specific
        stuff.
        """

        def inner(request, *args, **kwargs):

            # Let templates know this is projectadmin, and which project it is
            extra_context = {"projectadmin": True,
                             "project_name": self.project.short_name,
                             "project_pk": self.project.pk}

            # If there is existing extra_context, add this. but then remove it
            # from kwargs because otherwise you will get a "got two values for" exception
            if "extra_context" in kwargs:
                kwargs["extra_context"].update(extra_context)
            else:
                kwargs["extra_context"] = extra_context

            # certain standard admin urls cannot handle the extra_context var,
            # making an excpetion here
            no_extra_context = ["jsi18n", "view_on_site", "logout",
                                "password_change",
                                "password_change_done"]
            if request.resolver_match.url_name in no_extra_context:
                del kwargs["extra_context"]

            # Going for high ranking here in most unreadable line of python 2014
            # What would uncle bob say? Would he even survive? And how could Guido's
            # dream of clean readble code have turned so nightmarish? 
            return super(ProjectAdminSite2, self).admin_view(view)(request,
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
        return comicsiteadmin.change_view(request, str(self.project.pk), "",
                                          extra_context)

    def has_permission(self, request):
        """ For projectadmin, in addition to standard django checks, check if requesting
        user is an admin for this project    
        """
        standard_check = super(ProjectAdminSite2, self).has_permission(request)
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
            # return url(r'^admin/', include(projectadminsite.urls)),
        return pat

    def get_admin_patterns(self, project):
        """ get all url patterns for project, to use in urls.py
        
        """
        name = project.get_project_admin_instance_name()
        projectadminsite = ProjectAdminSite2(name=name, project=project)
        projectadminsite.register_comicmodels()

        urls = projectadminsite.get_urls()
        regex = r'^{}/admin/'.format(project.short_name.lower())

        urlpatterns = [
            url(regex, projectadminsite.urls)
        ]
        return urlpatterns


class ComicSiteAdminForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs=
                                                        {'rows': 4,
                                                         'cols': 80}),
                                  help_text="Short summary of this project,"
                                            " max 1024 characters.")
    disclaimer = forms.CharField(required=False,
                                 widget=forms.Textarea(attrs=
                                                       {'rows': 4,
                                                        'cols': 120}),
                                 help_text="'Under construction'-like "
                                           "banner to show on each page")

    short_name = forms.CharField(required=False,
                                 widget=forms.TextInput(attrs=
                                                        {'size': 30, })
                                 )

    class Meta:
        model = ComicSite
        fields = '__all__'


class ComicSiteAdmin(admin.ModelAdmin):
    # Make sure regular template overrides work. GuardedModelAdmin disables this
    # With change_form_template = None templates in templates/admin/comicsite/page
    # will be heeded again.
    change_form_template = None

    # make all textboxes wider because having them too small is stupid
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '100%'})}, }

    list_display = ('short_name', 'link', 'hidden')
    # list_filter = ['comicsite']
    form = ComicSiteAdminForm

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'logo',)
        }),
        ('Layout', {
            'classes': ('collapse',),
            'fields': ('header_image', 'skin', 'disclaimer',)
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('workshop_date', 'event_name', 'event_url',
                       'is_open_for_submissions', 'submission_page_name',
                       'number_of_submissions',
                       'last_submission_date',
                       'offers_data_download', 'number_of_downloads',
                       'publication_url', 'publication_journal_name',
                       )
        }),
        ('Users', {
            'classes': ('collapse',),
            'fields': (
                'manage_admin_link',
                'manage_participation_request_link',
                'use_registration_page',
                'require_participant_review',
                'registration_page_text',
            )
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('hidden', 'hide_signin', 'hide_footer',)
        }),
        ('Automated Evaluation', {
            'classes': ('collapse',),
            'fields': (
                'use_evaluation',
            )
        }),
    )
    readonly_fields = (
        "manage_admin_link", "link", )

    admin_manage_template = \
        'admin/comicmodels/admin_manage.html'

    def link(self, obj):
        """ link to current project, so you can easily view project """
        try:
            link_url = reverse('challenge-homepage', args=[obj.short_name])
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

        url = reverse("admin:comicmodels_comicsite_admins", args=[instance.pk],
                      current_app=instance.get_project_admin_instance_name())
        return "<a href={}>View, Add or Remove Administrators for this project</a>".format(
            url)

    manage_admin_link.allow_tags = True  # allow links
    manage_admin_link.short_description = "Admins"

    def get_queryset(self, request):
        """ overwrite this method to return only comicsites to which current user has access """
        qs = super(ComicSiteAdmin, self).get_queryset(request)

        if request.user.is_superuser:
            return qs
        else:
            qs = get_objects_for_user(request.user,
                                      'comicmodels.change_comicsite')
            qs = filter_projects_by_user_admin(qs, request.user)
            return qs

    def get_urls(self):
        """
        Extends standard admin model urls to manage admins and participants:
        """

        urls = super(ComicSiteAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = [
            url(r'^(?P<object_pk>.+)/admins/$',
                view=self.admin_site.admin_view(self.admin_add_view),
                name='%s_%s_admins' % info)
        ]
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
            'original': hasattr(obj, '__str__') and obj.__str__() or \
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
        User = get_user_model()
        admins = comicsite.get_admins()

        if request.method == 'POST' and 'submit_add_user' in request.POST:
            user_form = AdminManageForm(request.POST)
            if user_form.is_valid():
                user = user_form.cleaned_data['user']
                # add given user to admins group
                comicsite.add_admin(user)

                # give them the staff bit
                user.is_staff = True
                user.save()
                messages.add_message(request, messages.SUCCESS,
                                     'User "' + user.username + '"\
                                     is now an admin for ' + comicsite.short_name)

                # send signal to be picked up for example by email notifier
                new_admin.send(sender=self, adder=request.user, new_admin=user,
                               comicsite=comicsite
                               , site=get_current_site(request))



        elif request.method == 'POST' and 'submit_delete_user' in request.POST:
            user_form = AdminManageForm(request.POST)

            if user_form.is_valid():

                # add given user to admins group
                usernames_to_remove = request.POST.getlist('admins')
                removed = []

                msg2 = ""
                for username in usernames_to_remove:
                    if username == request.user.username:
                        msg2 = "Did not remove " + username + " because that's you."

                    else:

                        user = User.objects.get(username=username)
                        comicsite.remove_admin(user)
                        removed.append(username)

                        # send signal to be picked up for example by email notifier
                        removed_admin.send(sender=self, adder=request.user,
                                           removed_admin=user,
                                           comicsite=comicsite,
                                           site=get_current_site(request))

                msg = "Removed users [" + ", ".join(
                    removed) + "] from " + comicsite.short_name + \
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
                                  context, RequestContext(request,
                                                          current_app=self.admin_site.name))

    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.creator = request.user
        super(ComicSiteAdmin, self).save_model(request, obj, form, change)

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        """ overwrite this to inject some useful info message at first creation """
        if obj is None:
            messages.info(request,
                          'Please fill out the form to create a new project. <b>Required fields are bold.</b> Please save your project before adding pages or admins.',
                          extra_tags='safe')

        return super(ComicSiteAdmin, self).render_change_form(request, context,
                                                              add, change,
                                                              form_url, obj)


class AdminManageForm(forms.Form):
    admins = forms.CharField(required=False, widget=forms.SelectMultiple,
                             help_text="All admins for this project")
    User = get_user_model()
    user = forms.ModelChoiceField(queryset=User.objects.all(),
                                  empty_label="<user to add>", required=False)


# this variable is included in urls.py to get admin urls for each project in
# the database  
projectadminurls = AllProjectAdminSites()

admin.site.register(ComicSite, ComicSiteAdmin)
