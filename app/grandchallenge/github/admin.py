from django.contrib import admin

from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage


@admin.register(GitHubUserToken)
class GitHubUserTokenAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "access_token",
        "access_token_expires",
        "refresh_token",
        "refresh_token_expires",
    )
    list_display = ("user", "access_token_expires", "refresh_token_expires")
    search_fields = ("user__username",)


@admin.register(GitHubWebhookMessage)
class GitHubWebhookMessageAdmin(admin.ModelAdmin):
    list_display = (
        "created",
        "repo_name",
        "tag",
        "clone_status",
        "license_keys",
        "has_open_source_license",
        "user_error",
    )
    list_filter = ("clone_status",)
    search_fields = ("payload", "license_check_result")
    exclude = ("zipfile",)
    readonly_fields = ("payload", "clone_status")
