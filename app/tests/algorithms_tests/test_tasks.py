from datetime import timedelta
from pathlib import Path

import pytest
from actstream.models import Follow
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.algorithms.tasks import (
    create_algorithm_jobs,
    deactivate_old_algorithm_images,
    execute_algorithm_job_for_inputs,
    filter_archive_items_for_algorithm,
    send_failed_job_notification,
)
from grandchallenge.archives.models import ArchiveItem
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.tasks import validate_docker_image
from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.factories import (
    GroupFactory,
    ImageFactory,
    ImageFileFactory,
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
        interface = AlgorithmInterfaceFactory()
        ai.algorithm.interfaces.set([interface])

        create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.none(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=GPUTypeChoices.NO_GPU,
            requires_memory_gb=4,
            max_jobs=16,
        )
        assert Job.objects.count() == 0

    def test_no_algorithm_image_errors_out(self):
        with pytest.raises(RuntimeError):
            create_algorithm_jobs(
                algorithm_image=None,
                archive_items=ArchiveItem.objects.none(),
                time_limit=60,
                requires_gpu_type=GPUTypeChoices.NO_GPU,
                requires_memory_gb=4,
                max_jobs=16,
            )

    def test_creates_job_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        ci = ComponentInterface.objects.get(slug="generic-medical-image")
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        ai.algorithm.interfaces.set([interface])

        civ = ComponentInterfaceValueFactory(image=image, interface=ci)
        item = ArchiveItemFactory()
        item.values.add(civ)

        assert Job.objects.count() == 0
        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )
        assert Job.objects.count() == 1
        j = Job.objects.first()
        assert j.algorithm_image == ai
        assert j.creator is None
        assert j.algorithm_interface == interface
        assert (
            j.inputs.get(interface__slug="generic-medical-image").image
            == image
        )
        assert j.pk == jobs[0].pk

    def test_creates_job_for_multiple_interfaces_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        ci1 = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
        ci2 = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)
        ci3 = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)

        interface1 = AlgorithmInterfaceFactory(inputs=[ci1])
        interface2 = AlgorithmInterfaceFactory(inputs=[ci2])
        interface3 = AlgorithmInterfaceFactory(inputs=[ci3])
        interface4 = AlgorithmInterfaceFactory(inputs=[ci1, ci3])
        interface5 = AlgorithmInterfaceFactory(inputs=[ci1, ci2, ci3])
        ai.algorithm.interfaces.set(
            [interface1, interface2, interface3, interface4, interface5]
        )

        civ1 = ComponentInterfaceValueFactory(value=False, interface=ci1)
        civ2 = ComponentInterfaceValueFactory(image=image, interface=ci2)
        civ3 = ComponentInterfaceValueFactory(value="foo", interface=ci3)
        civ4 = ComponentInterfaceValueFactory()

        archive = ArchiveFactory()
        item1, item2, item3, item4, item5, item6 = (
            ArchiveItemFactory.create_batch(6, archive=archive)
        )
        item1.values.add(civ1)  # item for interface 1 only
        item2.values.add(civ2)  # item for interface 2 only
        item3.values.add(civ3)  # item for interface 3 only
        item4.values.set([civ1, civ3])  # item for interface 4 only
        item5.values.set([civ4])  # not a match for any interface
        item6.values.set([civ2, civ3])  # not a match for any interface

        assert Job.objects.count() == 0
        create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )
        assert Job.objects.count() == 4

        for j in Job.objects.all():
            assert j.algorithm_image == ai
            assert j.creator is None

        assert not (
            Job.objects.get(algorithm_interface=interface1).inputs.get().value
        )
        assert (
            Job.objects.get(algorithm_interface=interface2).inputs.get().image
            == image
        )
        assert (
            Job.objects.get(algorithm_interface=interface3).inputs.get().value
            == "foo"
        )
        assert (
            Job.objects.get(algorithm_interface=interface4).inputs.count() == 2
        )
        assert [False, "foo"] == list(
            Job.objects.get(algorithm_interface=interface4).inputs.values_list(
                "value", flat=True
            )
        )

    def test_is_idempotent(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        ci = ComponentInterface.objects.get(slug="generic-medical-image")
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        ai.algorithm.interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(image=image, interface=ci)
        item = ArchiveItemFactory()
        item.values.add(civ)

        assert Job.objects.count() == 0

        create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )

        assert Job.objects.count() == 1

        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )

        assert Job.objects.count() == 1
        assert len(jobs) == 0

    def test_extra_viewer_groups(self):
        ai = AlgorithmImageFactory()
        ci = ComponentInterface.objects.get(slug="generic-medical-image")
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        ai.algorithm.interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(interface=ci)
        item = ArchiveItemFactory()
        item.values.add(civ)
        groups = (GroupFactory(), GroupFactory(), GroupFactory())
        jobs = create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            extra_viewer_groups=groups,
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )
        for g in groups:
            assert jobs[0].viewer_groups.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_no_jobs_workflow(django_capture_on_commit_callbacks):
    ai = AlgorithmImageFactory()
    with django_capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.none(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )
    assert len(callbacks) == 0


@pytest.mark.django_db
def test_jobs_workflow(django_capture_on_commit_callbacks):
    ai = AlgorithmImageFactory()
    images = [ImageFactory(), ImageFactory()]
    ci = ComponentInterface.objects.get(slug="generic-medical-image")
    archive = ArchiveFactory()
    for im in images:
        item = ArchiveItemFactory(archive=archive)
        item.values.add(ComponentInterfaceValueFactory(image=im, interface=ci))

    interface = AlgorithmInterfaceFactory(inputs=[ci])
    ai.algorithm.interfaces.set([interface])

    with django_capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(
            algorithm_image=ai,
            archive_items=ArchiveItem.objects.all(),
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
            max_jobs=16,
        )
    assert len(callbacks) == 2


@pytest.mark.django_db
def test_algorithm(client, settings, django_capture_on_commit_callbacks):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    # Create the algorithm image
    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    user = UserFactory()
    ai.algorithm.add_editor(user)
    VerificationFactory(user=user, is_verified=True)

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
        inputs=[input_interface, heatmap_interface],
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
                **get_interface_form_data(
                    interface_slug=heatmap_interface.slug,
                    data=image_file.image.pk,
                ),
            },
        )

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    # There should be a single, successful job
    job = Job.objects.filter(algorithm_image=ai).get()

    assert job.stdout.endswith("Greetings from stdout")
    assert job.stderr.endswith('("Hello from stderr")')
    assert "UserWarning: Could not google: [Errno " in job.stderr
    assert job.error_message == ""
    assert job.status == job.SUCCESS
    assert job.exec_duration == timedelta(seconds=1337)
    assert job.invoke_duration == timedelta(seconds=1874)
    assert job.utilization.duration.total_seconds() > 0

    # The job should have two ComponentInterfaceValues,
    # one for the results.json and one for output.tif
    assert len(job.outputs.all()) == 2

    json_result_civ = job.outputs.get(interface=json_result_interface)
    assert json_result_civ.value

    heatmap_civ = job.outputs.get(interface=heatmap_interface)
    assert heatmap_civ.image.name == "input_file.tif"

    # We add another ComponentInterface with file value and run the algorithm again
    metrics_file = ComponentInterface.objects.get(slug="metrics-json-file")
    interface2 = AlgorithmInterfaceFactory(
        inputs=[input_interface, heatmap_interface],
        outputs=[
            json_result_interface,
            heatmap_interface,
            metrics_file,
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
                **get_interface_form_data(
                    interface_slug=heatmap_interface.slug,
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
    ).distinct()
    # There should be a single, successful job
    assert len(jobs) == 1

    # The job should have three ComponentInterfaceValues
    assert len(jobs[0].outputs.all()) == 3
    metrics_civ = jobs[0].outputs.get(interface=metrics_file)
    assert metrics_civ.value


@pytest.mark.django_db
def test_algorithm_with_invalid_output(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    ai = AlgorithmImageFactory(
        image=None,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    user = UserFactory()
    ai.algorithm.add_editor(user)
    VerificationFactory(user=user, is_verified=True)

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
def test_execute_algorithm_job_sets_on_failed_jobs(
    settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()

    # Create the algorithm image
    alg = AlgorithmImageFactory()
    alg.algorithm.add_editor(creator)

    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    civ = ComponentInterfaceValueFactory(interface=ci, value="foo")
    interface = AlgorithmInterfaceFactory(
        inputs=[ci], outputs=[ComponentInterfaceFactory()]
    )
    alg.algorithm.interfaces.add(interface)
    job = AlgorithmJobFactory(
        creator=creator,
        algorithm_image=alg,
        time_limit=alg.algorithm.time_limit,
        algorithm_interface=interface,
        status=Job.VALIDATING_INPUTS,
    )
    job.inputs.set([civ])

    with django_capture_on_commit_callbacks() as callbacks:
        execute_algorithm_job_for_inputs(job_pk=job.pk)

    # Sanity: task should run till execution
    assert len(callbacks) == 1
    assert "grandchallenge.components.tasks.provision_job" in str(callbacks[0])

    job.refresh_from_db()
    assert job.status == Job.PENDING
    assert (
        job.task_on_failure["task"]
        == "grandchallenge.algorithms.tasks.send_failed_job_notification"
    )  # Full task is tested somewhere else


@pytest.mark.django_db
class TestJobCreation:
    def test_interface_matching(self):
        ai1, ai2, ai3, ai4 = AlgorithmImageFactory.create_batch(4)
        ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
        interface1 = AlgorithmInterfaceFactory(inputs=[ci1])
        interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci2])
        interface3 = AlgorithmInterfaceFactory(inputs=[ci2, ci3, ci4])
        interface4 = AlgorithmInterfaceFactory(inputs=[ci2])

        ai1.algorithm.interfaces.set([interface1])
        ai2.algorithm.interfaces.set([interface1, interface2])
        ai3.algorithm.interfaces.set([interface1, interface3, interface4])
        ai4.algorithm.interfaces.set([interface4])

        archive = ArchiveFactory()
        i1, i2, i3, i4 = ArchiveItemFactory.create_batch(4, archive=archive)
        i1.values.add(
            ComponentInterfaceValueFactory(interface=ci1)
        )  # Valid for interface 1
        i2.values.set(
            [
                ComponentInterfaceValueFactory(interface=ci1),
                ComponentInterfaceValueFactory(interface=ci2),
            ]
        )  # valid for interface 2
        i3.values.set(
            [
                ComponentInterfaceValueFactory(interface=ci1),
                ComponentInterfaceValueFactory(
                    interface=ComponentInterfaceFactory()
                ),
            ]
        )  # valid for no interface, because of additional / mismatching interface
        i4.values.set(
            [
                ComponentInterfaceValueFactory(interface=ci2),
                ComponentInterfaceValueFactory(
                    interface=ComponentInterfaceFactory()
                ),
            ]
        )  # valid for no interface, because of additional / mismatching interface

        # filtered archive items depend on defined interfaces and archive item values
        filtered_archive_items = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai1,
            algorithm_model=None,
        )
        assert filtered_archive_items.keys() == {interface1}
        assert filtered_archive_items[interface1] == [i1]

        filtered_archive_items = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai2,
            algorithm_model=None,
        )
        assert filtered_archive_items.keys() == {interface1, interface2}
        assert filtered_archive_items[interface1] == [i1]
        assert filtered_archive_items[interface2] == [i2]

        filtered_archive_items = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai3,
            algorithm_model=None,
        )
        assert filtered_archive_items.keys() == {
            interface1,
            interface3,
            interface4,
        }
        assert filtered_archive_items[interface1] == [i1]
        assert filtered_archive_items[interface3] == []
        assert filtered_archive_items[interface4] == []

        filtered_archive_items = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai4,
            algorithm_model=None,
        )
        assert filtered_archive_items.keys() == {interface4}
        assert filtered_archive_items[interface4] == []

    def test_jobs_with_creator_ignored(self):
        alg = AlgorithmFactory()
        ai = AlgorithmImageFactory(algorithm=alg)
        cis = ComponentInterfaceFactory.create_batch(2)
        interface = AlgorithmInterfaceFactory(inputs=cis)
        ai.algorithm.interfaces.set([interface])

        civs1 = [ComponentInterfaceValueFactory(interface=c) for c in cis]
        civs2 = [ComponentInterfaceValueFactory(interface=c) for c in cis]

        j1 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            algorithm_interface=interface,
            time_limit=ai.algorithm.time_limit,
        )
        j1.inputs.set(civs1)
        # non-system job
        j2 = AlgorithmJobFactory(
            creator=UserFactory(),
            algorithm_image=ai,
            algorithm_interface=interface,
            time_limit=ai.algorithm.time_limit,
        )
        j2.inputs.set(civs2)

        archive = ArchiveFactory()
        item1, item2 = ArchiveItemFactory.create_batch(2, archive=archive)
        item1.values.set(civs1)  # non-system job already exists
        item2.values.set(civs2)  # non-system job should be ignored

        filtered_civ_sets = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai,
        )

        assert filtered_civ_sets.keys() == {interface}
        assert filtered_civ_sets[interface] == [item2]

    def test_existing_jobs(self, archive_items_and_jobs_for_interfaces):
        # image used for all jobs
        image = archive_items_and_jobs_for_interfaces.jobs_for_interface1[
            0
        ].algorithm_image

        filtered_civ_sets = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=image,
        )
        # this should return 1 archive item per interface
        # for which there is no job yet
        assert filtered_civ_sets == {
            archive_items_and_jobs_for_interfaces.interface1: [
                archive_items_and_jobs_for_interfaces.items_for_interface1[1]
            ],
            archive_items_and_jobs_for_interfaces.interface2: [
                archive_items_and_jobs_for_interfaces.items_for_interface2[1]
            ],
        }

    def test_model_filter_for_jobs_works(self):
        alg = AlgorithmFactory()
        ai = AlgorithmImageFactory(algorithm=alg)
        am = AlgorithmModelFactory(algorithm=alg)
        cis = ComponentInterfaceFactory.create_batch(2)
        interface = AlgorithmInterfaceFactory(inputs=cis)
        ai.algorithm.interfaces.set([interface])

        civs1 = [ComponentInterfaceValueFactory(interface=c) for c in cis]
        civs2 = [ComponentInterfaceValueFactory(interface=c) for c in cis]

        j1 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            algorithm_model=am,
            algorithm_interface=interface,
            time_limit=ai.algorithm.time_limit,
        )
        j1.inputs.set(civs1)
        j2 = AlgorithmJobFactory(
            creator=None,
            algorithm_image=ai,
            algorithm_interface=interface,
            time_limit=ai.algorithm.time_limit,
        )
        j2.inputs.set(civs2)

        archive = ArchiveFactory()
        item1, item2 = ArchiveItemFactory.create_batch(2, archive=archive)
        item1.values.set(civs1)  # Job already exists with image and model
        item2.values.set(civs2)  # Job exists but only with image

        filtered_civ_sets = filter_archive_items_for_algorithm(
            archive_items=ArchiveItem.objects.all(),
            algorithm_image=ai,
            algorithm_model=am,
        )

        assert filtered_civ_sets.keys() == {interface}
        assert filtered_civ_sets[interface] == [item2]


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
def test_deactivate_old_algorithm_images(django_capture_on_commit_callbacks):
    old_unused_image = AlgorithmImageFactory(is_in_registry=True)
    AlgorithmImageFactory(is_in_registry=False)  # already removed
    AlgorithmImageFactory(
        is_in_registry=True, algorithm__public=True
    )  # is public so should still work
    old_with_recent_job = AlgorithmImageFactory(is_in_registry=True)
    old_with_old_job = AlgorithmImageFactory(is_in_registry=True)

    AlgorithmJobFactory(algorithm_image=old_with_recent_job, time_limit=60)
    AlgorithmJobFactory(algorithm_image=old_with_old_job, time_limit=60)

    # Set old image and job dates
    old_created = now() - timedelta(days=400)
    AlgorithmImage.objects.update(created=old_created)
    Job.objects.update(created=old_created)

    # Create recent image and jobs
    AlgorithmImageFactory(is_in_registry=True)  # too new
    AlgorithmJobFactory(algorithm_image=old_with_recent_job, time_limit=60)

    with django_capture_on_commit_callbacks() as callbacks:
        deactivate_old_algorithm_images()

    expected_callbacks = {
        f"<bound method Signature.apply_async of grandchallenge.components.tasks.remove_container_image_from_registry(pk={image.pk!r}, app_label='algorithms', model_name='algorithmimage')>"
        # Private algorithm images not used for a long time, or ever, should be removed from the registry
        for image in {old_unused_image, old_with_old_job}
    }

    assert {str(callback) for callback in callbacks} == expected_callbacks
