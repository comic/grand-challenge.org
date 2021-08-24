from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.views.generic import DeleteView, FormView, ListView
from guardian.mixins import LoginRequiredMixin
from knox.models import AuthToken

from grandchallenge.api_tokens.forms import AuthTokenForm
from grandchallenge.subdomains.utils import reverse


class APITokenList(LoginRequiredMixin, ListView):
    model = AuthToken

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).prefetch_related(
            "session_set"
        )


class APITokenCreate(LoginRequiredMixin, FormView):
    template_name = "knox/authtoken_form.html"
    form_class = AuthTokenForm

    def form_valid(self, form):
        _, token = form.create_token(user=self.request.user)
        messages.add_message(
            self.request,
            messages.INFO,
            format_html(
                (
                    "Your new API token is:<br><br>"
                    "<pre>{}</pre>"
                    "Please treat this like a password and remove the key if "
                    "necessary. The key will not be visible again once this "
                    "message has been dismissed."
                ),
                token,
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("api-tokens:list")


class APITokenDelete(LoginRequiredMixin, DeleteView):
    model = AuthToken
    success_message = "Token successfully deleted"

    def get_object(self, queryset=None):
        return get_object_or_404(
            klass=AuthToken,
            token_key=self.kwargs["token_key"],
            user=self.request.user,
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("api-tokens:list")
