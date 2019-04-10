from django.contrib import messages
from django.shortcuts import redirect, render
from userena import views as userena_views

from grandchallenge.profiles.forms import EditProfileForm
from grandchallenge.subdomains.utils import reverse
from grandchallenge.profiles.utils import signin_redirect


def login_redirect(request):
    next_uri = request.GET.get("next")
    redirect_uri = signin_redirect(redirect=next_uri, user=request.user)
    return redirect(redirect_uri)


def profile(request):
    """
    Redirect to the profile page of the currently signed in user.
    """
    if request.user.is_authenticated:
        # print "username:", request.user.username
        # print "redirect to profile"
        return redirect("/accounts/" + request.user.username)

    else:
        return redirect("/accounts/signin")


def profile_edit_redirect(request):
    """
    Redirect to the profile edit page of the currently signed in user.
    """
    if request.user.is_authenticated:
        # print "username: ", request.user.username
        # print "redirect to profile edit"
        messages.add_message(
            request,
            messages.INFO,
            "Please fill-in the missing information in the form form below.",
        )
        return redirect("/accounts/" + request.user.username + "/edit")

    else:
        return redirect("accounts/signin")


def profile_edit(*args, **kwargs):
    kwargs["edit_profile_form"] = EditProfileForm
    return userena_views.profile_edit(*args, **kwargs)


def signup(request, extra_context=None, **kwargs):
    success = reverse("profile_signup_complete")
    response = userena_views.signup(
        request=request,
        extra_context=extra_context,
        success_url=success,
        **kwargs,
    )
    return response


def signin(request, **kwargs):
    redirect_signin_function = signin_redirect
    response = userena_views.signin(
        request=request,
        redirect_signin_function=redirect_signin_function,
        **kwargs,
    )
    return response


def signup_complete(request):
    response = render(request, "userena/signup_complete.html")
    return response
