import pytest
from django.contrib.auth.models import Group
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.factories import UserFactory


@pytest.mark.django_db(transaction=True)
def test_algorithm_image_data_migration(admin_user):
    executor = MigrationExecutor(connection)
    app = "algorithms"
    migrate_from = [(app, "0010_auto_20190827_1159")]
    migrate_to = [(app, "0011_algorithm_image_data_20190827_1236")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    user = UserFactory()
    OldAlgorithmImage = old_apps.get_model(app, "AlgorithmImage")  # noqa: N806
    old_ai = OldAlgorithmImage.objects.create(
        creator_id=user.pk,
        title="foo",
        description="my awesome algorithm",
        logo=get_temporary_image(),
    )

    assert old_ai

    # Reload
    executor.loader.build_graph()
    # Migrate forwards
    executor.migrate(migrate_to)

    new_apps = executor.loader.project_state(migrate_to).apps
    NewAlgorithm = new_apps.get_model(app, "Algorithm")  # noqa: N806

    new_alg = NewAlgorithm.objects.get(slug=old_ai.slug)

    assert new_alg
    assert new_alg.slug == old_ai.slug
    assert new_alg.title == old_ai.title
    assert new_alg.logo == old_ai.logo
    assert new_alg.workstation_id

    images = new_alg.algorithm_container_images.all()
    assert [i.pk for i in images] == [old_ai.pk]

    assert new_alg.editors_group
    assert new_alg.users_group

    assert user.groups.filter(pk=new_alg.editors_group.pk).exists()
    assert not user.groups.filter(pk=new_alg.users_group.pk).exists()


@pytest.mark.django_db
def test_algorithm_creators_group_exists(settings):
    assert Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
