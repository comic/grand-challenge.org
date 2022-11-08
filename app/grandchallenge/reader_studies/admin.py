from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerGroupObjectPermission,
    AnswerUserObjectPermission,
    DisplaySet,
    DisplaySetGroupObjectPermission,
    DisplaySetUserObjectPermission,
    Question,
    QuestionGroupObjectPermission,
    QuestionUserObjectPermission,
    ReaderStudy,
    ReaderStudyGroupObjectPermission,
    ReaderStudyPermissionRequest,
    ReaderStudyUserObjectPermission,
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
        "workstation",
    )
    list_filter = (
        "public",
        "is_educational",
        "allow_answer_modification",
        "allow_case_navigation",
        "workstation__slug",
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
    list_display = ("reader_study", "order")
    list_select_related = ("reader_study",)


admin.site.register(ReaderStudy, ReaderStudyAdmin)
admin.site.register(ReaderStudyUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    ReaderStudyGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(Question, QuestionsAdmin)
admin.site.register(QuestionUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(QuestionGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(Answer, AnswersAdmin)
admin.site.register(AnswerUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(AnswerGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(
    ReaderStudyPermissionRequest, ReaderStudyPermissionRequestAdmin
)
admin.site.register(DisplaySet, DisplaySetAdmin)
admin.site.register(DisplaySetUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    DisplaySetGroupObjectPermission, GroupObjectPermissionAdmin
)
