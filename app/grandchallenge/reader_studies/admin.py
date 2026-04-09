from django.conf import settings
from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerGroupObjectPermission,
    AnswerUserObjectPermission,
    CategoricalOption,
    DisplaySet,
    DisplaySetGroupObjectPermission,
    DisplaySetUserObjectPermission,
    Question,
    QuestionGroupObjectPermission,
    QuestionUserObjectPermission,
    ReaderStudy,
    ReaderStudyAlgorithm,
    ReaderStudyAlgorithmAlgorithmInterface,
    ReaderStudyAlgorithmImplementation,
    ReaderStudyGroupObjectPermission,
    ReaderStudyPermissionRequest,
    ReaderStudyUserObjectPermission,
)


@admin.register(ReaderStudy)
class ReaderStudyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "pk",
        "public",
        "is_educational",
        "instant_verification",
        "allow_answer_modification",
        "allow_case_navigation",
        "workstation",
    )
    list_filter = (
        "public",
        "is_educational",
        "instant_verification",
        "allow_answer_modification",
        "allow_case_navigation",
        "workstation__slug",
    )
    search_fields = ("title", "slug", "pk")
    readonly_fields = ("credits_consumed",)

    def get_form(self, *args, **kwargs):
        help_texts = {
            "max_credits": f"The maximum number of credits that may be consumed for "
            f"this reader study. Leave blank to allow unlimited usage. "
            f"The hourly rate is dependent on the use of interactive algorithms: "
            f"without interactive algorithms it's {settings.WORKSTATIONS_SESSION_CREDITS_PER_HOUR} credits per hour; "
            f"with interactive algorithms it's {settings.WORKSTATIONS_SESSION_INTERACTIVE_ALGORITHMS_CREDITS_PER_HOUR} credits per hour."
        }
        kwargs.update({"help_texts": help_texts})
        return super().get_form(*args, **kwargs)


@admin.register(Answer)
class AnswersAdmin(admin.ModelAdmin):
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
    search_fields = ("creator__username", "pk")


@admin.register(Question)
class QuestionsAdmin(admin.ModelAdmin):
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


@admin.register(ReaderStudyPermissionRequest)
class ReaderStudyPermissionRequestAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "reader_study")


@admin.register(DisplaySet)
class DisplaySetAdmin(admin.ModelAdmin):
    list_filter = ("reader_study__slug",)
    readonly_fields = ("id", "reader_study", "values")
    list_display = (
        "id",
        "order",
        "title",
        "reader_study",
    )
    list_select_related = ("reader_study",)


@admin.register(CategoricalOption)
class CategoricalOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "question", "default")


class ReaderStudyAlgorithmAlgorithmInterfaceInLine(admin.TabularInline):
    model = ReaderStudyAlgorithmAlgorithmInterface


@admin.register(ReaderStudyAlgorithm)
class ReaderStudyAlgorithmAdmin(admin.ModelAdmin):
    inlines = [ReaderStudyAlgorithmAlgorithmInterfaceInLine]


admin.site.register(ReaderStudyUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    ReaderStudyGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(ReaderStudyAlgorithmImplementation, admin.ModelAdmin)
admin.site.register(QuestionUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(QuestionGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(AnswerUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(AnswerGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(DisplaySetUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    DisplaySetGroupObjectPermission, GroupObjectPermissionAdmin
)
