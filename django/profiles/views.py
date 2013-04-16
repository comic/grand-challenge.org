from django.shortcuts import redirect

import pdb
import userena.views as userena_views

#FIXME: quick-n-dirty implementation to make things work for social-auth login redirect handling.

def profile(request):
    """
    Redirect to the profile page of the currently signed in user.
    """
    if request.user.is_authenticated():
        print "username: ", request.user.username
        return redirect('/accounts/'+request.user.username)
    else:
        return redirect('/accounts/signin')

def profile_edit(request):
    """
    Redirect to the profile edit page of the currently signed in user.
    """
    if request.user.is_authenticated():
        print "username: ", request.user.username
        return redirect('/accounts/'+request.user.username+'/edit')
    else:
        return redirect('accounts/signin')