from django.contrib import admin

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy


class ReaderStudyAdmin(admin.ModelAdmin):
    exclude = ("images",)


admin.site.register(ReaderStudy, ReaderStudyAdmin)
admin.site.register(Question)
admin.site.register(Answer)
