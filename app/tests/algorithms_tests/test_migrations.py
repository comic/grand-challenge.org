import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.utils import get_temporary_image


@pytest.mark.django_db(transaction=True)
def test_algorithm_image_data_migration(admin_user):
    executor = MigrationExecutor(connection)
    app = "algorithms"
    migrate_from = [(app, "0010_auto_20190827_1159")]
    migrate_to = [(app, "0011_algorithm_image_data_20190827_1236")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    OldAlgorithmImage = old_apps.get_model(app, "AlgorithmImage")
    old_ai = OldAlgorithmImage.objects.create(
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
    NewAlgorithm = new_apps.get_model(app, "Algorithm")

    new_alg = NewAlgorithm.objects.get(slug=old_ai.slug)

    assert new_alg
    assert new_alg.slug == old_ai.slug
    assert new_alg.title == old_ai.title
    assert new_alg.logo == old_ai.logo
    assert new_alg.workstation_id

    # TODO:check groups, users, and foreign keys
