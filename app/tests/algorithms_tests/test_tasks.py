import re
from pathlib import Path

import pytest
from actstream.models import Follow
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import (
    create_algorithm_jobs,
    create_algorithm_jobs_for_archive,
    execute_algorithm_job_for_inputs,
    filter_civs_for_algorithm,
    send_failed_job_notification,
)
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.tasks import (
    add_image_to_component_interface_value,
    validate_docker_image,
)
from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.factories import (
    GroupFactory,
    ImageFactory,
    ImageFileFactory,
    UploadSessionFactory,
    UserFactory,
)
from tests.utils import get_view_for_user, recurse_callbacks
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestCreateAlgorithmJobs:
    @property
    def default_input_interface(self):
        return ComponentInterface.objects.get(slug="generic-medical-image")

    def test_no_images_does_nothing(self):
        ai = AlgorithmImageFactory()
        create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=GPUTypeChoices.NO_GPU,
            requires_memory_gb=4,
        )
        assert Job.objects.count() == 0

    def test_no_algorithm_image_errors_out(self):
        with pytest.raises(RuntimeError):
            create_algorithm_jobs(
                algorithm_image=None,
                civ_sets=[],
                time_limit=60,
                requires_gpu_type=GPUTypeChoices.NO_GPU,
                requires_memory_gb=4,
            )

    def test_creates_job_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )
        ai.algorithm.inputs.set([interface])
        civ = ComponentInterfaceValueFactory(image=image, interface=interface)
        assert Job.objects.count() == 0
        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[{civ}],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
        assert Job.objects.count() == 1
        j = Job.objects.first()
        assert j.algorithm_image == ai
        assert j.creator is None
        assert (
            j.inputs.get(interface__slug="generic-medical-image").image
            == image
        )
        assert j.pk == jobs[0].pk

    def test_is_idempotent(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )
        civ = ComponentInterfaceValueFactory(image=image, interface=interface)

        assert Job.objects.count() == 0

        create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[{civ}],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )

        assert Job.objects.count() == 1

        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[{civ}],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )

        assert Job.objects.count() == 1
        assert len(jobs) == 0

    def test_extra_viewer_groups(self):
        ai = AlgorithmImageFactory()
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )
        civ = ComponentInterfaceValueFactory(interface=interface)
        groups = (GroupFactory(), GroupFactory(), GroupFactory())
        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[{civ}],
            extra_viewer_groups=groups,
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
        for g in groups:
            assert jobs[0].viewer_groups.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_no_jobs_workflow(django_capture_on_commit_callbacks):
    ai = AlgorithmImageFactory()
    with django_capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
    assert len(callbacks) == 0


@pytest.mark.django_db
def test_jobs_workflow(django_capture_on_commit_callbacks):
    ai = AlgorithmImageFactory()
    images = [ImageFactory(), ImageFactory()]
    interface = ComponentInterface.objects.get(slug="generic-medical-image")
    civ_sets = [
        {ComponentInterfaceValueFactory(image=im, interface=interface)}
        for im in images
    ]
    with django_capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=civ_sets,
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
    assert len(callbacks) == 2


@pytest.mark.flaky(reruns=3)
@pytest.mark.django_db
def test_algorithm(
    algorithm_image, client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    # Create the algorithm image
    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image=None)

        with open(algorithm_image, "rb") as f:
            ai.image.save(algorithm_image, ContentFile(f.read()))

    user = UserFactory()
    ai.algorithm.add_editor(user)
    VerificationFactory(user=user, is_verified=True)

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )
    ai.refresh_from_db()

    # Run the algorithm, it will create a results.json and an output.tif
    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )
    assign_perm("cases.view_image", user, image_file.image)

    input_interface = ComponentInterface.objects.get(
        slug="generic-medical-image"
    )
    json_result_interface = ComponentInterface.objects.get(
        slug="results-json-file"
    )
    heatmap_interface = ComponentInterface.objects.get(slug="generic-overlay")
    interface = AlgorithmInterfaceFactory(
        inputs=[input_interface],
        outputs=[json_result_interface, heatmap_interface],
    )
    ai.algorithm.interfaces.add(interface)

    with django_capture_on_commit_callbacks() as callbacks:
        get_view_for_user(
            viewname="algorithms:job-create",
            client=client,
            method=client.post,
            user=user,
            reverse_kwargs={
                "slug": ai.algorithm.slug,
                "interface_pk": interface.pk,
            },
            follow=True,
            data={
                **get_interface_form_data(
                    interface_slug=input_interface.slug,
                    data=image_file.image.pk,
                ),
            },
        )

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    jobs = Job.objects.filter(algorithm_image=ai).all()

    # There should be a single, successful job
    assert len(jobs) == 1

    assert jobs[0].stdout.endswith("Greetings from stdout")
    assert jobs[0].stderr.endswith('("Hello from stderr")')
    assert "UserWarning: Could not google: [Errno " in jobs[0].stderr
    assert jobs[0].error_message == ""
    assert jobs[0].status == jobs[0].SUCCESS

    # The job should have two ComponentInterfaceValues,
    # one for the results.json and one for output.tif
    assert len(jobs[0].outputs.all()) == 2

    json_result_civ = jobs[0].outputs.get(interface=json_result_interface)
    assert json_result_civ.value == {
        "entity": "out.tif",
        "metrics": {"abnormal": 0.19, "normal": 0.81},
    }

    heatmap_civ = jobs[0].outputs.get(interface=heatmap_interface)

    assert heatmap_civ.image.name == "output.tif"

    # We add another ComponentInterface with file value and run the algorithm again
    detection_interface = ComponentInterfaceFactory(
        store_in_database=False,
        relative_path="detection_results.json",
        title="detection-json-file",
        slug="detection-json-file",
        kind=ComponentInterface.Kind.ANY,
    )
    interface2 = AlgorithmInterfaceFactory(
        inputs=[input_interface],
        outputs=[
            json_result_interface,
            heatmap_interface,
            detection_interface,
        ],
    )
    ai.algorithm.interfaces.add(interface2)
    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )
    assign_perm("cases.view_image", user, image_file.image)

    with django_capture_on_commit_callbacks() as callbacks:
        get_view_for_user(
            viewname="algorithms:job-create",
            client=client,
            method=client.post,
            user=user,
            reverse_kwargs={
                "slug": ai.algorithm.slug,
                "interface_pk": interface2.pk,
            },
            follow=True,
            data={
                **get_interface_form_data(
                    interface_slug=input_interface.slug,
                    data=image_file.image.pk,
                ),
            },
        )

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    jobs = Job.objects.filter(
        algorithm_image=ai, inputs__image=image_file.image
    ).all()
    # There should be a single, successful job
    assert len(jobs) == 1

    # The job should have three ComponentInterfaceValues,
    # one with the detection_results store in the file
    assert len(jobs[0].outputs.all()) == 3
    detection_civ = jobs[0].outputs.get(interface=detection_interface)
    assert not detection_civ.value
    assert re.search("detection_results.*json$", detection_civ.file.name)


@pytest.mark.django_db
def test_algorithm_with_invalid_output(
    algorithm_image, client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    # Create the algorithm image
    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image=None)

        with open(algorithm_image, "rb") as f:
            ai.image.save(algorithm_image, ContentFile(f.read()))

    user = UserFactory()
    ai.algorithm.add_editor(user)
    VerificationFactory(user=user, is_verified=True)

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )
    ai.refresh_from_db()

    # Make sure the job fails when trying to upload an invalid file
    input_interface = ComponentInterface.objects.get(
        slug="generic-medical-image"
    )
    detection_interface = ComponentInterfaceFactory(
        store_in_database=False,
        relative_path="some_text.txt",
        slug="detection-json-file",
        kind=ComponentInterface.Kind.ANY,
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[input_interface], outputs=[detection_interface]
    )
    ai.algorithm.interfaces.add(interface)

    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )
    assign_perm("cases.view_image", user, image_file.image)

    with django_capture_on_commit_callbacks() as callbacks:
        get_view_for_user(
            viewname="algorithms:job-create",
            client=client,
            method=client.post,
            user=user,
            reverse_kwargs={
                "slug": ai.algorithm.slug,
                "interface_pk": interface.pk,
            },
            follow=True,
            data={
                **get_interface_form_data(
                    interface_slug=input_interface.slug,
                    data=image_file.image.pk,
                ),
            },
        )

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    jobs = Job.objects.filter(
        algorithm_image=ai, inputs__image=image_file.image, status=Job.FAILURE
    ).all()
    assert len(jobs) == 1
    assert (
        jobs.first().error_message
        == "The output file 'some_text.txt' is not valid json"
    )
    assert len(jobs[0].outputs.all()) == 0


@pytest.mark.django_db
def test_add_image_to_component_interface_value():
    # Override the celery settings
    us = RawImageUploadSessionFactory()
    ImageFactory(origin=us)
    ImageFactory(origin=us)
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    civ = ComponentInterfaceValueFactory(interface=ci, image=None, file=None)

    add_image_to_component_interface_value(
        component_interface_value_pk=civ.pk, upload_session_pk=us.pk
    )
    us.refresh_from_db()
    civ.refresh_from_db()
    assert us.error_message == "Image imports should result in a single image"
    assert civ.image is None

    us2 = RawImageUploadSessionFactory()
    image = ImageFactory(origin=us2)
    civ2 = ComponentInterfaceValueFactory(interface=ci, image=None, file=None)
    add_image_to_component_interface_value(
        component_interface_value_pk=civ2.pk, upload_session_pk=us2.pk
    )
    civ2.refresh_from_db()
    assert civ2.image == image


@pytest.mark.django_db
def test_execute_algorithm_job_for_missing_inputs(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()

    # Create the algorithm image
    alg = AlgorithmImageFactory()
    alg.algorithm.add_editor(creator)

    # create the job without value for the ComponentInterfaceValues
    ci = ComponentInterface.objects.get(slug="generic-medical-image")
    ComponentInterfaceValue.objects.create(interface=ci)
    interface = AlgorithmInterfaceFactory(
        inputs=[ci], outputs=[ComponentInterfaceFactory()]
    )
    alg.algorithm.interfaces.add(interface)
    job = AlgorithmJobFactory(
        creator=creator,
        algorithm_image=alg,
        time_limit=alg.algorithm.time_limit,
        algorithm_interface=interface,
    )
    execute_algorithm_job_for_inputs(job_pk=job.pk)

    # nothing happens since the input is missing
    job.refresh_from_db()
    assert job.status == Job.PENDING
    assert job.error_message == ""


@pytest.mark.django_db
class TestJobCreation:
    def test_unmatched_interface_filter(self):
        ai = AlgorithmImageFactory()
        cis = ComponentInterfaceFactory.create_batch(2)
        ai.algorithm.inputs.set(cis)

        civ_sets = [
            {},  # No interfaces
            {
                ComponentInterfaceValueFactory(interface=cis[0])
            },  # Missing interface
            {
                # OK
                ComponentInterfaceValueFactory(interface=cis[0]),
                ComponentInterfaceValueFactory(interface=cis[1]),
            },
            {
                # Unmatched interface
                ComponentInterfaceValueFactory(interface=cis[0]),
                ComponentInterfaceValueFactory(
                    interface=ComponentInterfaceFactory()
                ),
            },
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai, algorithm_model=None
        )

        assert filtered_civ_sets == [civ_sets[2]]

    def test_unmatched_interface_filter_subset(self):
        ai = AlgorithmImageFactory()
        cis = ComponentInterfaceFactory.create_batch(2)
        ai.algorithm.inputs.set(cis)

        civ_sets = [
            {
                # Extra interface
                ComponentInterfaceValueFactory(interface=cis[0]),
                ComponentInterfaceValueFactory(interface=cis[1]),
                ComponentInterfaceValueFactory(
                    interface=ComponentInterfaceFactory()
                ),
            }
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai, algorithm_model=None
        )

        assert len(filtered_civ_sets) == 1
        assert {civ.interface for civ in filtered_civ_sets[0]} == {*cis}

    def test_existing_jobs(self):
        alg = AlgorithmFactory()
        ai = AlgorithmImageFactory(algorithm=alg)
        am = AlgorithmModelFactory(algorithm=alg)
        cis = ComponentInterfaceFactory.create_batch(2)
        ai.algorithm.inputs.set(cis)

        civs1 = [ComponentInterfaceValueFactory(interface=c) for c in cis]
        civs2 = [ComponentInterfaceValueFactory(interface=c) for c in cis]
        civs3 = [ComponentInterfaceValueFactory(interface=c) for c in cis]

        j1 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            time_limit=ai.algorithm.time_limit,
        )
        j1.inputs.set(civs1)
        j2 = AlgorithmJobFactory(
            algorithm_image=ai, time_limit=ai.algorithm.time_limit
        )
        j2.inputs.set(civs2)
        j3 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            algorithm_model=am,
            time_limit=ai.algorithm.time_limit,
        )
        j3.inputs.set(civs3)

        civ_sets = [
            {civ for civ in civs1},  # Job already exists (system job)
            {
                civ for civ in civs2
            },  # Job already exists but with a creator set and hence should be ignored
            {
                civ for civ in civs3
            },  # Job exists but with an algorithm model set and should be ignored
            {
                # New values
                ComponentInterfaceValueFactory(interface=cis[0]),
                ComponentInterfaceValueFactory(interface=cis[1]),
            },
            {
                # Changed values
                civs1[0],
                ComponentInterfaceValueFactory(interface=cis[1]),
            },
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai, algorithm_model=None
        )

        assert sorted(filtered_civ_sets) == sorted(civ_sets[1:])

    def test_existing_jobs_with_algorithm_model(self):
        alg = AlgorithmFactory()
        ai = AlgorithmImageFactory(algorithm=alg)
        am = AlgorithmModelFactory(algorithm=alg)
        cis = ComponentInterfaceFactory.create_batch(2)
        ai.algorithm.inputs.set(cis)

        civs1 = [ComponentInterfaceValueFactory(interface=c) for c in cis]
        civs2 = [ComponentInterfaceValueFactory(interface=c) for c in cis]

        j1 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            algorithm_model=am,
            time_limit=ai.algorithm.time_limit,
        )
        j1.inputs.set(civs1)
        j2 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            time_limit=ai.algorithm.time_limit,
        )
        j2.inputs.set(civs2)

        civ_sets = [
            {civ for civ in civs1},  # Job already exists with image and model
            {
                civ
                for civ in civs2  # Job exists but only with image, so should be ignored
            },
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai, algorithm_model=am
        )

        assert filtered_civ_sets == sorted(civ_sets[1:])


@pytest.mark.django_db
def test_failed_job_notifications(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()
    editor = UserFactory()

    # Create the algorithm image
    ai = AlgorithmImageFactory()
    ai.algorithm.add_editor(editor)

    job = Job.objects.create(
        creator=creator,
        algorithm_image=ai,
        input_civ_set=[],
        time_limit=ai.algorithm.time_limit,
        requires_gpu_type=ai.algorithm.job_requires_gpu_type,
        requires_memory_gb=ai.algorithm.job_requires_memory_gb,
    )

    # mark job as failed
    job.status = Job.FAILURE
    job.save()

    with django_capture_on_commit_callbacks(execute=True):
        send_failed_job_notification(job_pk=job.pk)

    # 1 notification for the job creator
    notification = Notification.objects.get()
    assert notification.user == creator
    assert (
        f"Unfortunately one of the jobs for algorithm {ai.algorithm.title} failed with an error"
        in notification.print_notification(user=creator.username)
    )

    # delete notifications for easier testing below
    Notification.objects.all().delete()
    # unsubscribe creator from job notifications
    _ = get_view_for_user(
        viewname="api:follow-detail",
        client=client,
        method=client.patch,
        reverse_kwargs={
            "pk": Follow.objects.filter(user=creator, flag="job-active")
            .get()
            .pk
        },
        content_type="application/json",
        data={"flag": "job-inactive"},
        user=creator,
    )

    job = Job.objects.create(
        creator=creator,
        algorithm_image=ai,
        input_civ_set=[],
        time_limit=ai.algorithm.time_limit,
        requires_gpu_type=ai.algorithm.job_requires_gpu_type,
        requires_memory_gb=ai.algorithm.job_requires_memory_gb,
    )

    # mark job as failed
    job.status = Job.FAILURE
    job.save()

    with django_capture_on_commit_callbacks(execute=True):
        send_failed_job_notification(job_pk=job.pk)

    with pytest.raises(ObjectDoesNotExist):
        Notification.objects.get()


@pytest.mark.django_db
def test_importing_same_sha_fails(
    settings, django_capture_on_commit_callbacks, algorithm_io_image
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    alg = AlgorithmFactory()

    im1, im2 = AlgorithmImageFactory.create_batch(
        2, algorithm=alg, image__from_path=algorithm_io_image
    )

    for im in [im1, im2]:
        with django_capture_on_commit_callbacks(execute=True):
            validate_docker_image(
                pk=im.pk,
                app_label=im._meta.app_label,
                model_name=im._meta.model_name,
                mark_as_desired=False,
            )

    im1.refresh_from_db()
    im2.refresh_from_db()

    assert len(im1.image_sha256) == 71
    assert im1.image_sha256 == im2.image_sha256
    assert im1.is_manifest_valid is True
    assert im1.status == ""
    assert im2.is_manifest_valid is False
    assert im2.status == (
        "This container image has already been uploaded. "
        "Please re-activate the existing container image or upload a new version."
    )


@pytest.mark.django_db
def test_archive_job_gets_gpu_and_memory_set(
    django_capture_on_commit_callbacks,
):
    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        algorithm__job_requires_gpu_type=GPUTypeChoices.V100,
        algorithm__job_requires_memory_gb=1337,
    )
    archive = ArchiveFactory()

    session = UploadSessionFactory()
    im = ImageFactory()
    session.image_set.set([im])

    input_interface = ComponentInterface.objects.get(
        slug="generic-medical-image"
    )
    civ = ComponentInterfaceValueFactory(image=im, interface=input_interface)

    archive_item = ArchiveItemFactory(archive=archive)
    with django_capture_on_commit_callbacks(execute=True):
        archive_item.values.add(civ)

    archive.algorithms.set([algorithm_image.algorithm])

    create_algorithm_jobs_for_archive(archive_pks=[archive.pk])

    job = Job.objects.get()

    assert job.requires_gpu_type == GPUTypeChoices.V100
    assert job.requires_memory_gb == 1337
