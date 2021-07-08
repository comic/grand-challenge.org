import pytz
from django import forms


class TimezoneForm(forms.Form):
    timezone = forms.ChoiceField(
        choices=((v, v) for v in pytz.all_timezones), required=True
    )
