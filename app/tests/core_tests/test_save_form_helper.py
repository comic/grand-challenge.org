import pytest
from crispy_forms.layout import Layout, Submit
from django.forms import CharField, Form

from grandchallenge.core.forms import SaveFormInitMixin


class SimpleForm(SaveFormInitMixin, Form):
    name = CharField()


class DynamicFieldForm(SaveFormInitMixin, Form):
    """Form that adds fields after super().__init__()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dynamic"] = CharField()


class DynamicFieldMixin:
    """Mixin that adds fields, simulating AdditionalInputsMixin."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from_mixin"] = CharField()


class MixinOrderAForm(SaveFormInitMixin, DynamicFieldMixin, Form):
    """SaveFormInitMixin first in MRO."""

    pass


class MixinOrderBForm(DynamicFieldMixin, SaveFormInitMixin, Form):
    """SaveFormInitMixin second in MRO."""

    pass


class CustomLayoutForm(SaveFormInitMixin, Form):
    name = CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            "name",
            Submit("save", "Go"),
        )


@pytest.mark.parametrize(
    "form_class",
    (
        SimpleForm,
        DynamicFieldForm,
        CustomLayoutForm,
        MixinOrderAForm,
        MixinOrderBForm,
    ),
)
def test_save_form_helper_always_sets_disable_attribute(form_class):
    form = form_class(data={})
    assert form.helper.attrs["gc-disable-after-submit"] is True


def test_dynamic_fields_included_in_default_layout():
    form = DynamicFieldForm(data={})
    layout = form.helper.layout
    field_names = [field for field in layout[0].fields]
    assert "dynamic" in field_names


def test_custom_layout_preserves_disable_attribute():
    form = CustomLayoutForm(data={})
    assert form.helper.attrs["gc-disable-after-submit"] is True
    # The custom layout is used, not the default
    assert len(form.helper.layout.fields) == 2  # "name" + Submit


def test_mixin_ordering_does_not_matter():
    """Fields from DynamicFieldMixin are included regardless of MRO order."""
    form_a = MixinOrderAForm(data={})
    form_b = MixinOrderBForm(data={})

    layout_a = form_a.helper.layout
    layout_b = form_b.helper.layout

    # Both should include from_mixin in their default layout
    fields_a = [field for field in layout_a[0].fields]
    fields_b = [field for field in layout_b[0].fields]

    assert "from_mixin" in fields_a
    assert "from_mixin" in fields_b
