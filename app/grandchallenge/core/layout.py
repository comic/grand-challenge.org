from crispy_forms.layout import TEMPLATE_PACK, LayoutObject
from django.template.loader import render_to_string


class Formset(LayoutObject):
    template = "layout/formset.html"

    def __init__(self, formset_name_in_context, template=None):
        self.formset_name_in_context = formset_name_in_context
        self.fields = []
        if template:
            self.template = template

    def render(self, form, context, template_pack=TEMPLATE_PACK):
        formset = context[self.formset_name_in_context]
        return render_to_string(self.template, {"formset": formset})
