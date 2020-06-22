import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from grandchallenge.algorithms.models import Result
from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.factories import ImageFactory, UserFactory


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


@pytest.mark.django_db
def test_algroithm_results_migration():
    j1, j2 = AlgorithmJobFactory(), AlgorithmJobFactory()

    # Create the old style interface
    j1_input, j2_input = j1.inputs.first().image, j2.inputs.first().image
    j1.image = j1.inputs.first().image
    j2.image = j2.inputs.first().image
    j1.save()
    j2.save()
    j1.inputs.clear()
    j2.inputs.clear()

    # Create the outputs
    im1, im2 = ImageFactory(), ImageFactory()
    a1 = Result.objects.create(
        job=j1, output="Output 1", public=True, comment="Comment 1"
    )
    a1.images.add(im1, im2)
    Result.objects.create(
        job=j2, output="Output 2", public=False, comment="Comment 2"
    )

    j1.refresh_from_db()
    j2.refresh_from_db()

    assert len(j1.inputs.all()) == 0
    assert len(j1.outputs.all()) == 0
    assert j1.image
    assert j1.public is False
    assert j1.comment == ""

    assert len(j2.inputs.all()) == 0
    assert len(j2.outputs.all()) == 0
    assert j2.image
    assert j2.public is False
    assert j2.comment == ""

    call_command("migrate_algorithm_results")

    j1.refresh_from_db()
    j2.refresh_from_db()

    assert len(j1.inputs.all()) == 1
    assert len(j1.outputs.all()) == 3
    assert j1.inputs.first().image == j1_input
    assert (
        j1.outputs.filter(interface__slug="results-json-file").first().value
        == "Output 1"
    )
    assert j1.image is None
    assert j1.public is True
    assert j1.comment == "Comment 1"

    assert len(j2.inputs.all()) == 1
    assert len(j2.outputs.all()) == 1
    assert j2.inputs.first().image == j2_input
    assert (
        j2.outputs.filter(interface__slug="results-json-file").first().value
        == "Output 2"
    )
    assert j2.image is None
    assert j2.public is False
    assert j2.comment == "Comment 2"
