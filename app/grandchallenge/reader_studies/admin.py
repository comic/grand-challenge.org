from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.reader_studies.models import (
    Answer,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)


class ReaderStudyAdmin(GuardedModelAdmin):
    exclude = ("images",)


class AnswersAdmin(GuardedModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "question",
        "creator",
        "is_ground_truth",
    )
    list_filter = (
        "is_ground_truth",
        "question__reader_study__slug",
    )
    list_select_related = ("question__reader_study",)
    readonly_fields = (
        "images",
        "creator",
        "answer",
        "answer_image",
        "question",
        "score",
    )
    search_fields = ("creator__username",)


class QuestionsAdmin(GuardedModelAdmin):
    list_filter = (
        "answer_type",
        "required",
        "reader_study__slug",
    )
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
    readonly_fields = (
        "user",
        "reader_study",
    )


admin.site.register(ReaderStudy, ReaderStudyAdmin)
admin.site.register(Question, QuestionsAdmin)
admin.site.register(Answer, AnswersAdmin)
admin.site.register(
    ReaderStudyPermissionRequest, ReaderStudyPermissionRequestAdmin
)
