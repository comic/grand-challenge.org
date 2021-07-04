from django.contrib import admin

from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage


class GitHubUserTokenAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "access_token",
        "access_token_expires",
        "refresh_token",
        "refresh_token_expires",
    )
    list_display = (
        "user",
        "access_token_expires",
        "refresh_token_expires",
    )
    search_fields = ("user__username",)


class GitHubWebhookMessageAdmin(admin.ModelAdmin):
    exclude = ("zipfile",)
    readonly_fields = ("payload",)


admin.site.register(GitHubUserToken, GitHubUserTokenAdmin)
admin.site.register(GitHubWebhookMessage, GitHubWebhookMessageAdmin)
