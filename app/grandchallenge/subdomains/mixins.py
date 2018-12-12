from django.http import Http404
from django.utils.translation import gettext as _


class ChallengeSubdomainObjectMixin:
    def get_object(self, queryset=None):
        try:
            obj = super().get_object(queryset=queryset)
        except AttributeError:
            # Could not be found with the usual parameters
            if queryset is None:
                queryset = self.get_queryset()

            # Filter by the request challenge
            slug_field = self.get_slug_field()
            queryset = queryset.filter(
                **{slug_field: self.request.challenge.short_name}
            )

            try:
                # Get the single item from the filtered queryset
                obj = queryset.get()
            except queryset.model.DoesNotExist:
                raise Http404(
                    _("No %(verbose_name)s found matching the query")
                    % {"verbose_name": queryset.model._meta.verbose_name}
                )

        return obj
