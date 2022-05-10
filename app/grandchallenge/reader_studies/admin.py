from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)


class ReaderStudyAdmin(GuardedModelAdmin):
    exclude = ("images",)
    list_display = (
        "title",
        "slug",
        "pk",
        "public",
        "is_educational",
        "allow_answer_modification",
        "allow_case_navigation",
    )
    list_filter = (
        "public",
        "is_educational",
        "allow_answer_modification",
        "allow_case_navigation",
    )
    search_fields = ("title", "slug", "pk")


class AnswersAdmin(GuardedModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "question", "creator", "is_ground_truth")
    list_filter = ("is_ground_truth", "question__reader_study__slug")
    list_select_related = ("question__reader_study",)
    readonly_fields = (
        "creator",
        "answer",
        "answer_image",
        "question",
        "score",
        "display_set",
    )
    search_fields = ("creator__username",)


class QuestionsAdmin(GuardedModelAdmin):
    list_filter = ("answer_type", "required", "reader_study__slug")
    readonly_fields = ("reader_study",)
    list_display = (
        "question_text",
        "image_port",
        "reader_study",
        "answer_type",
        "required",
        "order",
    )
    list_select_related = ("reader_study",)


class ReaderStudyPermissionRequestAdmin(GuardedModelAdmin):
    readonly_fields = ("user", "reader_study")


class DisplaySetAdmin(GuardedModelAdmin):
    list_filter = ("reader_study__slug",)
    readonly_fields = ("reader_study", "values")
    list_display = (
        "reader_study",
        "order",
    )
    list_select_related = ("reader_study",)


admin.site.register(ReaderStudy, ReaderStudyAdmin)
admin.site.register(Question, QuestionsAdmin)
admin.site.register(Answer, AnswersAdmin)
admin.site.register(
    ReaderStudyPermissionRequest, ReaderStudyPermissionRequestAdmin
)
admin.site.register(DisplaySet, DisplaySetAdmin)
