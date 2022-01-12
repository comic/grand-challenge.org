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
    list_display = (
        "created",
        "clone_status",
        "has_open_source_license",
        "licence_check_result",
        "error",
    )
    list_filter = (
        "clone_status",
        "has_open_source_license",
    )
    search_fields = ("payload",)
    exclude = ("zipfile",)
    readonly_fields = ("payload", "clone_status")


admin.site.register(GitHubUserToken, GitHubUserTokenAdmin)
admin.site.register(GitHubWebhookMessage, GitHubWebhookMessageAdmin)
