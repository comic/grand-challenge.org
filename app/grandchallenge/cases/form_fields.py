from django.forms import ChoiceField

from grandchallenge.cases.widgets import (
    ImageSourceChoiceWidget,
    ImageWidgetChoices,
)


class ImageSourceChoiceField(ChoiceField):
    widget = ImageSourceChoiceWidget(attrs={"class": "custom-select"})

    def __init__(
        self,
        *args,
        current_socket_value=None,
        required=True,
        **kwargs,
    ):
        self.current_socket_value = current_socket_value

        choices = kwargs.pop("choices", [])

        if current_socket_value is None:
            choice = ImageWidgetChoices.UNDEFINED
            choices.append((choice.value, choice.label))
        else:
            choices.append(
                (
                    ImageWidgetChoices.IMAGE_SELECTED.value,
                    current_socket_value.title,
                )
            )

        for choice in [
            ImageWidgetChoices.IMAGE_SEARCH,
            ImageWidgetChoices.IMAGE_UPLOAD,
        ]:
            choices.append((choice.value, choice.label))

        super().__init__(
            *args,
            required=required,
            choices=choices,
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        if value == ImageWidgetChoices.IMAGE_SELECTED:
            return self.current_socket_value.image
        else:
            return value
