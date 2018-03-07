from itertools import chain

from auth_mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView

from comicmodels.models import Page, RegistrationRequest, ComicSite
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from comicsite.views import site_get_standard_vars


class ParticipantsList(UserIsChallengeAdminMixin, ListView):
    def get_queryset(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_participants().select_related('user_profile')


class RegistrationRequestCreate(LoginRequiredMixin, SuccessMessageMixin,
                                CreateView):
    model = RegistrationRequest
    fields = ()
    success_message = (
        'You have requested to participate in this challenge. '
        'You will receive an email when this has been reviewed by the '
        'challenge organisers.'
    )

    def get_success_url(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_absolute_url()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.project = ComicSite.objects.get(
            pk=self.request.project_pk)
        return super().form_valid(form)


class RegistrationRequestList(UserIsChallengeAdminMixin, ListView):
    model = RegistrationRequest

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(project__pk=self.request.project_pk))
        return queryset


class RegistrationRequestUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin,
                                UpdateView):
    model = RegistrationRequest
    fields = ('status',)
    success_message = 'Registration successfully updated'

    def get_success_url(self):
        return reverse(
            'participants:registration-list',
            kwargs={
                'challenge_short_name': self.object.project.short_name,
            }
        )


##################################################
#
# Legacy functions, moved from comicsite/views.py,
# all use the template tag which should be removed
#
##################################################


def _register(request, challenge_short_name):
    """ Register the current user for given comicsite """

    # TODO: check whether user is allowed to register, maybe wait for verification,
    # send email to admins of new registration

    [site, pages, metafooterpages] = site_get_standard_vars(
        challenge_short_name)
    if request.user.is_authenticated():
        if site.require_participant_review:
            currentpage = _register_after_approval(request, site)
        else:
            currentpage = _register_directly(request, site)

    else:
        if "user_just_registered" in request.GET:
            # show message to use activation mail first, then refresh the page
            html = """<h2> Please activate your account </h2> 
            <p>An activation link has been sent to the email adress you provided.
            Please use this link to activate your account.</p> 
            
            After activating your account, click <a href="{0}">here to continue</a>  
            """.format("")

            currentpage = Page(comicsite=site, title="activate_your_account",
                               display_title="activate your account",
                               html=html)
        else:
            html = "you need to be logged in to use this url"
            currentpage = Page(comicsite=site, title="please_log_in",
                               display_title="Please log in", html=html)

    return render(
        request,
        'page.html',
        {
            'site': site,
            'currentpage': currentpage,
            "pages": pages,
        },
    )


def _register_directly(request, project):
    if request.user.is_authenticated():
        project.add_participant(request.user)
        title = "registration_successful"
        display_title = "registration successful"
        html = "<p> You are now registered for " + project.short_name + "<p>"
    else:
        title = "registration_unsuccessful"
        display_title = "registration unsuccessful"
        html = "<p><b>ERROR:</b>You need to be signed in to register<p>"

    currentpage = Page(comicsite=project, title=title,
                       display_title=display_title, html=html)
    return currentpage


def _register_after_approval(request, project):
    title = "registration requested"
    display_title = "registration requested"

    pending = RegistrationRequest.objects.get_pending_registration_requests(
        request.user, project)
    accepted = RegistrationRequest.objects.get_accepted_registration_requests(
        request.user, project)

    pending_or_accepted = list(chain(pending, accepted))

    if pending_or_accepted:
        html = pending_or_accepted[0].status_to_string()
        pass  # do not add another request
    else:
        reg_request = RegistrationRequest()
        reg_request.project = project
        reg_request.user = request.user
        reg_request.save()
        from comicsite.models import \
            send_participation_request_notification_email
        send_participation_request_notification_email(request, reg_request)

        html = "<p> A participation request has been sent to the " + project.short_name + " organizers. You will receive an email when your request has been reviewed<p>"

    currentpage = Page(comicsite=project, title=title,
                       display_title=display_title, html=html)
    return currentpage
