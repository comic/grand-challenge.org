from django.shortcuts import redirect
from django.contrib import messages


import pdb
import userena.views as userena_views


REDIRECT_FIELD_NAME = 'next'

#FIXME: quick-n-dirty implementation to make things work for social-auth login redirect handling.


def profile(request):
    """
    Redirect to the profile page of the currently signed in user.
    """
    if request.user.is_authenticated():
        print "username: ", request.user.username
        print "redirect to profile"
        return redirect('/accounts/'+request.user.username)
    else:
        return redirect('/accounts/signin')


def profile_edit(request):
    """
    Redirect to the profile edit page of the currently signed in user.
    """
    if request.user.is_authenticated():
        print "username: ", request.user.username
        print "redirect to profile edit"
        messages.add_message(request, messages.INFO, "Please fill-in the missing information in the form form below.")
        return redirect('/accounts/'+request.user.username+'/edit')
    else:
        return redirect('accounts/signin')
