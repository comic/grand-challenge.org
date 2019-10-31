from django.contrib import admin

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy

admin.site.register(ReaderStudy)
admin.site.register(Question)
admin.site.register(Answer)
