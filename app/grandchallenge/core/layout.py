from crispy_forms.layout import LayoutObject
from django.template.loader import render_to_string


class Formset(LayoutObject):
    template = "layout/formset.html"

    def __init__(self, formset):
        self.formset = formset

    def render(self, *args, **kwargs):
        return render_to_string(self.template, {"formset": self.formset})
