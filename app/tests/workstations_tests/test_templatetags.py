import pytest
from django.shortcuts import render

from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.templatetags.workstations import (
    get_workstation_path_and_query_string,
    workstation_session_control_data,
)
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.archives_tests.factories import ArchiveItemFactory
from tests.factories import (
    ImageFactory,
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)


def test_workstation_query_for_reader_studies(settings):
    reader_study = ReaderStudyFactory.build(
        workstation_config=WorkstationConfigFactory.build()
    )
    config = WorkstationConfigFactory.build()
    user = UserFactory.build()

    pqs = get_workstation_path_and_query_string(
        reader_study=reader_study, user=user
    )
    assert "&" in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/{reader_study.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_USER_QUERY_PARAM}={user.username}"
        in pqs.query_string
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={reader_study.workstation_config.pk}"
        in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(reader_study=reader_study)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/{reader_study.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={reader_study.workstation_config.pk}"
        in pqs.query_string
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        not in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(
        reader_study=reader_study, config=config
    )
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/{reader_study.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={reader_study.workstation_config.pk}"
        not in pqs.query_string
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        in pqs.query_string
    )

    reader_study.workstation_config = None

    pqs = get_workstation_path_and_query_string(reader_study=reader_study)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/{reader_study.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}" not in pqs.query_string
    )


def test_workstation_query_for_display_sets(settings):
    reader_study = ReaderStudyFactory.build(
        workstation_config=WorkstationConfigFactory.build()
    )
    config = WorkstationConfigFactory.build()
    display_set = DisplaySetFactory.build(reader_study=reader_study)

    pqs = get_workstation_path_and_query_string(display_set=display_set)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_DISPLAY_SET_PATH_PARAM}/{display_set.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={reader_study.workstation_config.pk}"
        in pqs.query_string
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        not in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(
        display_set=display_set, config=config
    )
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_DISPLAY_SET_PATH_PARAM}/{display_set.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={reader_study.workstation_config.pk}"
        not in pqs.query_string
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        in pqs.query_string
    )

    reader_study.workstation_config = None

    pqs = get_workstation_path_and_query_string(display_set=display_set)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_DISPLAY_SET_PATH_PARAM}/{display_set.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}" not in pqs.query_string
    )


def test_workstation_query_for_archive_items(settings):
    config = WorkstationConfigFactory.build()
    archive_item = ArchiveItemFactory.build()

    pqs = get_workstation_path_and_query_string(
        archive_item=archive_item, config=config
    )
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_ARCHIVE_ITEM_PATH_PARAM}/{archive_item.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(archive_item=archive_item)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_ARCHIVE_ITEM_PATH_PARAM}/{archive_item.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}" not in pqs.query_string
    )


def test_workstation_query_for_algorithms(settings):
    algorithm_job = AlgorithmJobFactory.build(time_limit=60)
    config = WorkstationConfigFactory.build()

    pqs = get_workstation_path_and_query_string(algorithm_job=algorithm_job)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_ALGORITHM_JOB_PATH_PARAM}/{algorithm_job.pk}"
        in pqs.path
    )

    pqs = get_workstation_path_and_query_string(
        algorithm_job=algorithm_job, config=config
    )
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_ALGORITHM_JOB_PATH_PARAM}/{algorithm_job.pk}"
        in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        in pqs.query_string
    )


def test_workstation_query_for_images(settings):
    image, overlay = ImageFactory.build_batch(2)
    config = WorkstationConfigFactory.build()

    pqs = get_workstation_path_and_query_string(image=image)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_BASE_IMAGE_PATH_PARAM}/{image.pk}" in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        not in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(image=image)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_BASE_IMAGE_PATH_PARAM}/{image.pk}" in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        not in pqs.query_string
    )

    pqs = get_workstation_path_and_query_string(image=image, config=config)
    assert "&" not in pqs.query_string
    assert (
        f"{settings.WORKSTATIONS_BASE_IMAGE_PATH_PARAM}/{image.pk}" in pqs.path
    )
    assert (
        f"{settings.WORKSTATIONS_CONFIG_QUERY_PARAM}={config.pk}"
        in pqs.query_string
    )


@pytest.mark.django_db
def test_workstation_session_control_data():
    wk = WorkstationFactory()
    obj = ReaderStudyFactory()

    with pytest.raises(TypeError):
        workstation_session_control_data()

    with pytest.raises(TypeError):
        workstation_session_control_data(workstation=wk)

    with pytest.raises(TypeError):
        workstation_session_control_data(context_object=obj)

    data = workstation_session_control_data(
        workstation=wk,
        context_object=obj,
    )
    url = reverse(
        "workstations:workstation-session-create", kwargs={"slug": wk.slug}
    )
    assert (
        data
        == f' data-session-control data-create-session-url="{url}" data-workstation-path="" data-workstation-query="" data-workstation-window-identifier="workstation-{obj._meta.app_label}"'
    )
    assert "timeout" not in data

    data2 = workstation_session_control_data(
        workstation=wk, context_object=obj, reader_study=obj, timeout=200
    )
    assert (
        data2
        == f' data-session-control data-create-session-url="{url}" data-workstation-path="reader-study/{obj.pk}" data-workstation-query="" data-workstation-window-identifier="workstation-{obj._meta.app_label}" data-timeout="200"'
    )


@pytest.mark.django_db
def test_workstation_session_control_data_tag_in_context(rf):
    workstation = WorkstationFactory()
    image = ImageFactory()
    request = rf.get("/foo/")
    response = render(
        request,
        "workstation_button.html",
        {"workstation": workstation, "image": image},
    )
    data = workstation_session_control_data(
        workstation=workstation, context_object=image, image=image
    )
    assert data in str(response.content)
