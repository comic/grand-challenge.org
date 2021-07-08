from django.views.generic import FormView

from grandchallenge.timezones.forms import TimezoneForm


class SetTimezone(FormView):
    form_class = TimezoneForm
    template_name = "timezones/set_timezone_form.html"

    def form_valid(self, form):
        self.request.session["timezone"] = form.cleaned_data["timezone"]
        return super().form_valid(form=form)

    def get_success_url(self):
        return "/"
