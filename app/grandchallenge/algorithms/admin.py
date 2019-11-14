from django.contrib import admin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    Job,
    Result,
)

admin.site.register(Algorithm)
admin.site.register(AlgorithmImage)
admin.site.register(Job)
admin.site.register(Result)
