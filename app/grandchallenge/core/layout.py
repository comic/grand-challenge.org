from crispy_forms.layout import LayoutObject
from django.template.loader import render_to_string


class Formset(LayoutObject):
    template = "layout/formset.html"

    def __init__(self, *args, formset, can_add_another, **kwargs):
        super().__init__(*args, **kwargs)
        self._formset = formset
        self._can_add_another = can_add_another

    def render(self, *args, **kwargs):
        return render_to_string(
            self.template,
            {
                "formset": self._formset,
                "can_add_another": self._can_add_another,
            },
        )
