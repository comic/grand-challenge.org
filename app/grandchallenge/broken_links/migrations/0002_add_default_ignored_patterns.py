from django.db import migrations

PATTERNS = [
    r".*\.(php|cgi|asp).*",
    r"^/phpmyadmin.*",
    r"^/gen204.*",
    r"^/wp-content.*",
    r"^/wp.*",
    r"^/wordpress/.*",
    r"(?i)^/old/.*",
    r".*/trackback.*",
    r"^/site/.*",
    r"^/media/cache/.*",
    r"^/favicon.ico$",
]


def add_ignored_patterns(apps, schema_editor):
    IgnoredPattern = apps.get_model(  # noqa: N806
        "broken_links", "IgnoredPattern"
    )
    for pattern in PATTERNS:
        IgnoredPattern.objects.create(pattern=pattern)


def remove_ignored_patterns(apps, schema_editor):
    IgnoredPattern = apps.get_model(  # noqa: N806
        "broken_links", "IgnoredPattern"
    )
    IgnoredPattern.objects.filter(pattern__in=PATTERNS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("broken_links", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            add_ignored_patterns, remove_ignored_patterns, elidable=True
        ),
    ]
