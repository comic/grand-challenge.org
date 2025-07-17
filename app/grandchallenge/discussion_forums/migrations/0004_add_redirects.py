from django.db import migrations

from grandchallenge.subdomains.utils import reverse


def add_redirects_for_old_forums_and_topics(apps, schema_editor):
    Forum = apps.get_model("discussion_forums", "Forum")  # noqa: N806
    ForumTopic = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopic"
    )
    Redirect = apps.get_model("redirects", "Redirect")  # noqa: N806
    Site = apps.get_model("sites", "Site")  # noqa: N806

    site = Site.objects.get_current()

    batch_size = 500
    redirects_to_add = []
    n_created = 0

    for forum in Forum.objects.filter(source_object__isnull=False):
        redirects_to_add.append(
            Redirect(
                site=site,
                old_path=f"/forums/forum/{forum.source_object.slug}-{forum.source_object.pk}/",
                new_path=reverse(
                    "discussion-forums:topic-list",
                    kwargs={
                        "challenge_short_name": forum.linked_challenge.short_name
                    },
                ),
            )
        )
        if len(redirects_to_add) >= batch_size:
            Redirect.objects.bulk_create(redirects_to_add)
            n_created += len(redirects_to_add)
            print(f"Created {n_created} new forum redirects")
            redirects_to_add = []

    if redirects_to_add:
        Redirect.objects.bulk_create(redirects_to_add)
        n_created += len(redirects_to_add)
        print(f"Created {n_created} new forum redirects.")
        redirects_to_add = []

    for topic in ForumTopic.objects.filter(source_object__isnull=False):
        redirects_to_add.append(
            Redirect(
                site=site,
                old_path=f"/forums/forum/{topic.source_object.forum.slug}-{topic.source_object.forum.pk}/topic/{topic.source_object.slug}-{topic.source_object.pk}/",
                new_path=reverse(
                    "discussion-forums:topic-post-list",
                    kwargs={
                        "challenge_short_name": topic.forum.linked_challenge.short_name,
                        "slug": topic.slug,
                    },
                ),
            )
        )
        if len(redirects_to_add) >= batch_size:
            Redirect.objects.bulk_create(redirects_to_add)
            n_created += len(redirects_to_add)
            print(f"Created {n_created} new topic redirects")
            redirects_to_add = []

    if redirects_to_add:
        Redirect.objects.bulk_create(redirects_to_add)
        n_created += len(redirects_to_add)
        print(f"Created {n_created} new topic redirects.")

    print("Finished adding redirects.")


class Migration(migrations.Migration):
    dependencies = [
        ("discussion_forums", "0003_add_auto_now"),
    ]

    operations = [
        migrations.RunPython(
            add_redirects_for_old_forums_and_topics, elidable=True
        ),
    ]
