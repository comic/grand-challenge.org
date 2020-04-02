from django.contrib import admin

from grandchallenge.reader_studies.models import (
    Answer,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)


class ReaderStudyAdmin(admin.ModelAdmin):
    exclude = ("images",)


class AnswersAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "question",
        "creator",
    )
    list_filter = ("question__reader_study__slug",)
    list_select_related = ("question__reader_study",)
    readonly_fields = ("images", "creator", "answer", "question", "score")
    search_fields = ("creator__username",)


class QuestionsAdmin(admin.ModelAdmin):
    list_filter = ("reader_study__slug",)
    readonly_fields = ("reader_study",)


admin.site.register(ReaderStudy, ReaderStudyAdmin)
admin.site.register(Question, QuestionsAdmin)
admin.site.register(Answer, AnswersAdmin)
admin.site.register(ReaderStudyPermissionRequest)
