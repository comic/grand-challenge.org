from django.conf import settings
from django.db import migrations


def assign_review_perm_to_reviewers_group(apps, schema_editor):
    ChallengeRequest = apps.get_model(  # noqa: N806
        "challenges", "ChallengeRequest"
    )
    ChallengeRequestGroupObjectPermission = apps.get_model(  # noqa: N806
        "challenges", "ChallengeRequestGroupObjectPermission"
    )
    Group = apps.get_model("auth", "Group")  # noqa: N806
    Permission = apps.get_model("auth", "Permission")  # noqa: N806

    challenge_requests = ChallengeRequest.objects.all()

    if not challenge_requests.exists():
        return

    try:
        reviewers_group = Group.objects.get(
            name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
        )
    except Group.DoesNotExist:
        return

    review_permission = Permission.objects.get(
        codename="review_challengerequest",
        content_type__app_label="challenges",
    )

    for challenge_request in challenge_requests:
        ChallengeRequestGroupObjectPermission.objects.get_or_create(
            content_object=challenge_request,
            group=reviewers_group,
            permission=review_permission,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0069_alter_challengerequest_abstract_and_more"),
    ]

    operations = [
        migrations.RunPython(
            assign_review_perm_to_reviewers_group,
            elidable=True,
        )
    ]
