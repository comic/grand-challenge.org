from enum import StrEnum

from django.forms import MultiWidget, Script
from django.forms.widgets import Select, TextInput


class SourceSelect(Select):
    template_name = "components/warning_select.html"

    class Media:
        js = (Script("components/js/source_select.mjs", type="module"),)


class SearchWidgetSuffixes(StrEnum):
    INPUT = "search-term"
    CHOICE = "selected-choice"


class FileSearchInputWidget(TextInput):
    def get_context(self, name, value, attrs):
        attrs["placeholder"] = "Search by full pk or (partial) file name"
        context = super().get_context(name, value, attrs)
        css_class = context["widget"]["attrs"].get("class", "")
        # When the MultiField marks the data invalid, the is-invalid class is
        # added to all subwidgets; however, the search input is never "invalid"
        # because that data will not be processed.
        context["widget"]["attrs"]["class"] = css_class.replace(
            "is-invalid", ""
        )
        return context


class SearchSelect(Select):
    template_name = "components/search_select.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        css_class = context["widget"]["attrs"].get("class", "")
        # Fix invalid icon overlapping with custom select controls
        context["widget"]["attrs"]["class"] = css_class.replace(
            "form-control", ""
        )
        context["widget"]["selected_object_pk"] = value
        return context


class FileSearchMultiWidget(MultiWidget):
    template_name = "components/file_search_multi_widget.html"

    def __init__(self, attrs=None, prefixed_interface_slug=None):
        widgets = {
            SearchWidgetSuffixes.INPUT.value: FileSearchInputWidget(),
            SearchWidgetSuffixes.CHOICE.value: SearchSelect(
                attrs={"class": "custom-select"}
            ),
        }
        super().__init__(widgets, attrs)
        self.prefixed_interface_slug = prefixed_interface_slug

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["prefixed_interface_slug"] = self.prefixed_interface_slug
        return context

    def decompress(self, value):
        if value:
            return value
        return ["", ""]
