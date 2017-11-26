from django.contrib import messages
from django.shortcuts import redirect

def login_redirect(request):
    next = request.GET.get('next', '/')
    return redirect(next)

def profile(request):
    """
    Redirect to the profile page of the currently signed in user.
    """
    if request.user.is_authenticated():
        # print "username:", request.user.username
        # print "redirect to profile"
        return redirect('/accounts/' + request.user.username)
    else:
        return redirect('/accounts/signin')


def profile_edit(request):
    """
    Redirect to the profile edit page of the currently signed in user.
    """
    if request.user.is_authenticated():
        # print "username: ", request.user.username
        # print "redirect to profile edit"
        messages.add_message(request, messages.INFO, "Please fill-in the missing information in the form form below.")
        return redirect('/accounts/' + request.user.username + '/edit')
    else:
        return redirect('accounts/signin')
