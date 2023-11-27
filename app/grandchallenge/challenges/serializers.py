from datetime import datetime

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField, URLField

from grandchallenge.challenges.models import Challenge


class PublicChallengeSerializer(serializers.ModelSerializer):
    url = URLField(source="get_absolute_url", read_only=True)
    publications = SerializerMethodField()
    submission_types = SerializerMethodField()
    start_date = SerializerMethodField()
    end_date = SerializerMethodField()
    modified = SerializerMethodField()
    incentives = SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "api_url",
            "url",
            "slug",
            "title",
            "description",
            "public",
            "status",
            "logo",
            "submission_types",
            "start_date",
            "end_date",
            "publications",
            "created",
            "modified",
            "incentives",
        ]

    def get_publications(self, obj) -> list[str]:
        return [p.identifier.url for p in obj.publications.all()]

    def get_start_date(self, obj) -> datetime | None:
        try:
            return min(
                p.submissions_open_at
                for p in obj.visible_phases
                if p.submissions_open_at
            )
        except ValueError:
            # No submission open set
            return None

    def get_end_date(self, obj) -> datetime | None:
        if any(p.submissions_close_at is None for p in obj.visible_phases):
            return None
        else:
            try:
                return max(
                    p.submissions_close_at
                    for p in obj.visible_phases
                    if p.submissions_close_at
                )
            except ValueError:
                # No Phases
                return None

    def get_submission_types(self, obj) -> list[str]:
        return list(
            {
                phase.get_submission_kind_display()
                for phase in obj.visible_phases
            }
        )

    def get_modified(self, obj) -> datetime:
        try:
            return max(
                obj.modified,
                max(p.modified for p in obj.visible_phases if p.modified),
            )
        except ValueError:
            # No Phases
            return obj.modified

    def get_incentives(self, obj) -> list[str]:
        return [incentive.incentive for incentive in obj.incentives.all()]
