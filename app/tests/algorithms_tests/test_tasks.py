import re
from io import BytesIO
from pathlib import Path

import pytest
from actstream.models import Follow
from django.core.files.base import File
from django.test import TestCase
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.exceptions import ImageImportError
from grandchallenge.algorithms.models import DEFAULT_INPUT_INTERFACE_SLUG, Job
from grandchallenge.algorithms.tasks import (
    add_images_to_component_interface_value,
    create_algorithm_jobs,
    execute_algorithm_job_for_inputs,
    filter_civs_for_algorithm,
    run_algorithm_job_for_inputs,
    send_failed_job_notification,
)
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import (
    GroupFactory,
    ImageFactory,
    ImageFileFactory,
    UserFactory,
)
from tests.utils import get_view_for_user, recurse_callbacks


@pytest.mark.django_db
class TestCreateAlgorithmJobs:
    @property
    def default_input_interface(self):
        return ComponentInterface.objects.get(
            slug=DEFAULT_INPUT_INTERFACE_SLUG
        )

    def test_no_images_does_nothing(self):
        ai = AlgorithmImageFactory()
        create_algorithm_jobs(algorithm_image=ai, civ_sets=[])
        assert Job.objects.count() == 0

    def test_civ_existing_does_nothing(self):
        image = ImageFactory()
        ai = AlgorithmImageFactory()
        j = AlgorithmJobFactory(creator=ai.creator, algorithm_image=ai)
        civ = ComponentInterfaceValueFactory(
            interface=self.default_input_interface, image=image
        )
        j.inputs.set([civ])
        assert Job.objects.count() == 1
        run_algorithm_job_for_inputs(job_pk=j.pk, upload_pks=[])
        assert Job.objects.count() == 1

    def test_creates_job_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        civ = ComponentInterfaceValueFactory(
            image=image, interface=ai.algorithm.inputs.get()
        )
        assert Job.objects.count() == 0
        jobs = create_algorithm_jobs(algorithm_image=ai, civ_sets=[{civ}])
        assert Job.objects.count() == 1
        j = Job.objects.first()
        assert j.algorithm_image == ai
        assert j.creator is None
        assert (
            j.inputs.get(interface__slug=DEFAULT_INPUT_INTERFACE_SLUG).image
            == image
        )
        assert j.pk == jobs[0].pk

    def test_is_idempotent(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        civ = ComponentInterfaceValueFactory(
            image=image, interface=ai.algorithm.inputs.get()
        )
        assert Job.objects.count() == 0
        create_algorithm_jobs(algorithm_image=ai, civ_sets=[{civ}])
        assert Job.objects.count() == 1
        jobs = create_algorithm_jobs(algorithm_image=ai, civ_sets=[{civ}])
        assert Job.objects.count() == 1
        assert len(jobs) == 0

    def test_gets_creator_from_session(self):
        ai = AlgorithmImageFactory()
        riu = RawImageUploadSessionFactory()
        riu.image_set.add(ImageFactory(), ImageFactory())
        civ_sets = [
            {
                ComponentInterfaceValueFactory(
                    image=image, interface=ai.algorithm.inputs.get()
                )
            }
            for image in riu.image_set.all()
        ]
        create_algorithm_jobs(
            algorithm_image=ai, civ_sets=civ_sets, creator=riu.creator,
        )
        j = Job.objects.first()
        assert j.creator == riu.creator

    def test_extra_viewer_groups(self):
        ai = AlgorithmImageFactory()
        civ = ComponentInterfaceValueFactory(
            interface=ai.algorithm.inputs.get()
        )
        groups = (GroupFactory(), GroupFactory(), GroupFactory())
        jobs = create_algorithm_jobs(
            algorithm_image=ai, civ_sets=[{civ}], extra_viewer_groups=groups
        )
        for g in groups:
            assert jobs[0].viewer_groups.filter(pk=g.pk).exists()

    def test_create_jobs_is_limited(self):
        user, editor = UserFactory(), UserFactory()

        algorithm_image = AlgorithmImageFactory()

        algorithm_image.algorithm.credits_per_job = 400
        algorithm_image.algorithm.save()

        algorithm_image.algorithm.add_editor(editor)

        def create_upload(upload_creator):
            riu = RawImageUploadSessionFactory(creator=upload_creator)

            for _ in range(3):
                ImageFactory(origin=riu),

            riu.save()

            interface = algorithm_image.algorithm.inputs.get()

            return [
                {ComponentInterfaceValueFactory(image=im, interface=interface)}
                for im in riu.image_set.all()
            ]

        assert Job.objects.count() == 0

        # Create an upload session as editor; should not be limited
        upload = create_upload(editor)
        create_algorithm_jobs(
            algorithm_image=algorithm_image, civ_sets=upload, creator=editor,
        )

        assert Job.objects.count() == 3

        # Create an upload session as user; should be limited
        upload_2 = create_upload(user)
        create_algorithm_jobs(
            algorithm_image=algorithm_image, civ_sets=upload_2, creator=user,
        )

        # An additional 2 jobs should be created (standard nr of credits is 1000
        # per user per month).
        assert Job.objects.count() == 5

        # As an editor you should not be limited
        algorithm_image.algorithm.add_editor(user)

        # The job that was skipped on the previous run should now be accepted
        create_algorithm_jobs(
            algorithm_image=algorithm_image, civ_sets=upload_2, creator=user,
        )
        assert Job.objects.count() == 6


class TestCreateJobsWorkflow(TestCase):
    def test_no_jobs_workflow(self):
        ai = AlgorithmImageFactory()
        with capture_on_commit_callbacks() as callbacks:
            create_algorithm_jobs(algorithm_image=ai, civ_sets=[])
        assert len(callbacks) == 0

    def test_jobs_workflow(self):
        ai = AlgorithmImageFactory()
        images = [ImageFactory(), ImageFactory()]
        civ_sets = [
            {
                ComponentInterfaceValueFactory(
                    image=im, interface=ai.algorithm.inputs.get()
                )
            }
            for im in images
        ]
        with capture_on_commit_callbacks() as callbacks:
            create_algorithm_jobs(algorithm_image=ai, civ_sets=civ_sets)
        assert len(callbacks) == 2


@pytest.mark.django_db
def test_algorithm(client, algorithm_image, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )

    # We should not be able to download image
    with pytest.raises(NotImplementedError):
        _ = alg.image.url

    # Run the algorithm, it will create a results.json and an output.tif
    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif",
    )
    civ = ComponentInterfaceValueFactory(
        image=image_file.image, interface=alg.algorithm.inputs.get(), file=None
    )
    assert civ.interface.slug == "generic-medical-image"

    with capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(algorithm_image=alg, civ_sets=[{civ}])
    recurse_callbacks(callbacks=callbacks)

    jobs = Job.objects.filter(algorithm_image=alg).all()

    # There should be a single, successful job
    assert len(jobs) == 1

    assert jobs[0].stdout.endswith("Greetings from stdout\n")
    assert jobs[0].stderr.endswith('("Hello from stderr")\n')
    assert jobs[0].error_message == ""
    assert jobs[0].status == jobs[0].SUCCESS

    # The job should have two ComponentInterfaceValues,
    # one for the results.json and one for output.tif
    assert len(jobs[0].outputs.all()) == 2
    json_result_interface = ComponentInterface.objects.get(
        slug="results-json-file"
    )
    json_result_civ = jobs[0].outputs.get(interface=json_result_interface)
    assert json_result_civ.value == {
        "entity": "out.tif",
        "metrics": {"abnormal": 0.19, "normal": 0.81},
    }

    heatmap_interface = ComponentInterface.objects.get(slug="generic-overlay")
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
    alg.algorithm.outputs.add(detection_interface)
    alg.save()
    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )
    civ = ComponentInterfaceValueFactory(
        image=image_file.image, interface=alg.algorithm.inputs.get(), file=None
    )

    with capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(algorithm_image=alg, civ_sets=[{civ}])
    recurse_callbacks(callbacks=callbacks)

    jobs = Job.objects.filter(
        algorithm_image=alg, inputs__image=image_file.image
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
def test_algorithm_with_invalid_output(client, algorithm_image, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    assert Job.objects.count() == 0

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )

    # Make sure the job fails when trying to upload an invalid file
    detection_interface = ComponentInterfaceFactory(
        store_in_database=False,
        relative_path="some_text.txt",
        slug="detection-json-file",
        kind=ComponentInterface.Kind.ANY,
    )
    alg.algorithm.outputs.add(detection_interface)
    alg.save()
    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )
    civ = ComponentInterfaceValueFactory(
        image=image_file.image, interface=alg.algorithm.inputs.get(), file=None
    )

    with capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(algorithm_image=alg, civ_sets=[{civ}])
    recurse_callbacks(callbacks=callbacks)

    jobs = Job.objects.filter(
        algorithm_image=alg, inputs__image=image_file.image, status=Job.FAILURE
    ).all()
    assert len(jobs) == 1
    assert (
        jobs.first().error_message
        == "The file produced at /output/some_text.txt is not valid json"
    )
    assert len(jobs[0].outputs.all()) == 0


@pytest.mark.django_db
def test_algorithm_multiple_inputs(
    client, algorithm_io_image, settings, component_interfaces
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()

    assert Job.objects.count() == 0

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_io_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )
    alg.algorithm.add_editor(creator)

    alg.algorithm.inputs.set(ComponentInterface.objects.all())
    alg.algorithm.outputs.set(
        [ComponentInterface.objects.get(slug="results-json-file")]
    )
    # create the job
    job = Job.objects.create(creator=creator, algorithm_image=alg)

    expected = []
    for ci in ComponentInterface.objects.exclude(
        kind=InterfaceKindChoices.ZIP
    ):
        if ci.kind in InterfaceKind.interface_type_image():
            image_file = ImageFileFactory(
                file__from_path=Path(__file__).parent
                / "resources"
                / "input_file.tif"
            )
            job.inputs.add(
                ComponentInterfaceValueFactory(
                    interface=ci, image=image_file.image
                )
            )
            expected.append("file")
        elif ci.kind in InterfaceKind.interface_type_file():
            civ = ComponentInterfaceValueFactory(interface=ci)
            civ.file.save("test", File(BytesIO(b"")))
            civ.save()
            job.inputs.add(civ)
            expected.append("file")
        else:
            job.inputs.add(
                ComponentInterfaceValueFactory(interface=ci, value="test")
            )
            expected.append("test")

    with capture_on_commit_callbacks() as callbacks:
        run_algorithm_job_for_inputs(job_pk=job.pk, upload_pks=[])
    recurse_callbacks(callbacks=callbacks)

    job.refresh_from_db()
    assert job.error_message == ""
    assert job.status == job.SUCCESS

    # Remove fake value for score
    output_dict = job.outputs.first().value
    output_dict.pop("score")

    assert {f"/input/{x.relative_path}" for x in job.inputs.all()} == set(
        output_dict.keys()
    )
    assert sorted(
        map(lambda x: x if x != {} else "json", output_dict.values(),)
    ) == sorted(expected)


@pytest.mark.django_db
def test_algorithm_input_image_multiple_files(
    client, algorithm_io_image, settings, component_interfaces
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()

    assert Job.objects.count() == 0

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_io_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )
    alg.algorithm.add_editor(creator)

    alg.algorithm.inputs.set(ComponentInterface.objects.all())
    # create the job
    job = Job.objects.create(creator=creator, algorithm_image=alg)
    us = RawImageUploadSessionFactory()

    ImageFactory(origin=us), ImageFactory(origin=us)
    ci = ComponentInterface.objects.get(slug=DEFAULT_INPUT_INTERFACE_SLUG)

    civ = ComponentInterfaceValue.objects.create(interface=ci)
    job.inputs.add(civ)

    with pytest.raises(ImageImportError):
        with capture_on_commit_callbacks(execute=True):
            run_algorithm_job_for_inputs(
                job_pk=job.pk, upload_pks={civ.pk: us.pk}
            )

    # TODO: celery errorhandling with the .on_error seems to not work when
    # TASK_ALWAYS_EAGER is set to True. The error function does get called
    # when running normally, but unfortunately it is currently hard to test.
    # We should look into this at some point.

    # job = Job.objects.first()
    # assert job.status == job.FAILURE
    # assert job.error_message == (
    #     "Job can't be started, input is missing for "
    #     "['Generic Medical Image'] "
    #     "ValueError('Image imports should result in a single image')"
    # )


@pytest.mark.django_db
def test_add_images_to_component_interface_value():
    # Override the celery settings
    us = RawImageUploadSessionFactory()
    ImageFactory(origin=us), ImageFactory(origin=us)
    ci = ComponentInterface.objects.get(slug=DEFAULT_INPUT_INTERFACE_SLUG)

    civ = ComponentInterfaceValueFactory(interface=ci, image=None, file=None)

    with pytest.raises(ImageImportError) as err:
        add_images_to_component_interface_value(
            component_interface_value_pk=civ.pk, upload_session_pk=us.pk
        )
    assert "Image imports should result in a single image" in str(err)
    assert civ.image is None

    us2 = RawImageUploadSessionFactory()
    image = ImageFactory(origin=us2)
    civ2 = ComponentInterfaceValueFactory(interface=ci, image=None, file=None)
    add_images_to_component_interface_value(
        component_interface_value_pk=civ2.pk, upload_session_pk=us2.pk
    )
    civ2.refresh_from_db()
    assert civ2.image == image


@pytest.mark.django_db
def test_execute_algorithm_job_for_inputs(
    client, algorithm_io_image, settings
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_io_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )
    alg.algorithm.add_editor(creator)

    # create the job without value for the ComponentInterfaceValues
    ci = ComponentInterface.objects.get(slug=DEFAULT_INPUT_INTERFACE_SLUG)
    civ = ComponentInterfaceValue.objects.create(interface=ci)
    job = Job.objects.create(creator=creator, algorithm_image=alg)
    job.inputs.add(civ)
    execute_algorithm_job_for_inputs(job_pk=job.pk)

    job.refresh_from_db()
    assert job.status == Job.FAILURE
    assert "Job can't be started, input is missing for " in job.error_message


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
            civ_sets=civ_sets, algorithm_image=ai
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
            },
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai
        )

        assert len(filtered_civ_sets) == 1
        assert {civ.interface for civ in filtered_civ_sets[0]} == {*cis}

    def test_existing_jobs(self):
        ai = AlgorithmImageFactory()
        cis = ComponentInterfaceFactory.create_batch(2)
        ai.algorithm.inputs.set(cis)

        civs = [ComponentInterfaceValueFactory(interface=c) for c in cis]

        j = AlgorithmJobFactory(algorithm_image=ai)
        j.inputs.set(civs)

        civ_sets = [
            civs,  # Job already exists
            {
                # New values
                ComponentInterfaceValueFactory(interface=cis[0]),
                ComponentInterfaceValueFactory(interface=cis[1]),
            },
            {
                # Changed values
                civs[0],
                ComponentInterfaceValueFactory(interface=cis[1]),
            },
        ]

        filtered_civ_sets = filter_civs_for_algorithm(
            civ_sets=civ_sets, algorithm_image=ai
        )

        assert filtered_civ_sets == civ_sets[1:]


@pytest.mark.django_db
def test_failed_job_notifications(client, algorithm_io_image, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()
    editor = UserFactory()

    # Create the algorithm image
    algorithm_container, sha256 = algorithm_io_image
    alg = AlgorithmImageFactory(
        image__from_path=algorithm_container, image_sha256=sha256, ready=True
    )
    alg.algorithm.add_editor(editor)

    job = Job.objects.create(creator=creator, algorithm_image=alg)

    # mark job as failed
    job.status = Job.FAILURE
    job.save()

    with capture_on_commit_callbacks(execute=True):
        send_failed_job_notification(job_pk=job.pk)

    # 2 notifications: for the editor of the algorithm and the job creator
    assert Notification.objects.count() == 2
    assert creator.username in str(Notification.objects.all())
    assert editor.username in str(Notification.objects.all())
    for notification in Notification.objects.all():
        assert (
            f"Unfortunately one of the jobs for algorithm {alg.algorithm.title} failed with an error"
            in notification.print_notification(user=notification.user)
        )

    # delete notifications for easier testing below
    Notification.objects.all().delete()
    # unsubscribe editor from job notifications
    _ = get_view_for_user(
        viewname="api:follow-detail",
        client=client,
        method=client.patch,
        reverse_kwargs={
            "pk": Follow.objects.filter(user=editor, flag="job-active")
            .get()
            .pk
        },
        content_type="application/json",
        data={"flag": "job-inactive"},
        user=editor,
    )

    job = Job.objects.create(creator=creator, algorithm_image=alg)

    # mark job as failed
    job.status = Job.FAILURE
    job.save()

    with capture_on_commit_callbacks(execute=True):
        send_failed_job_notification(job_pk=job.pk)

    assert Notification.objects.count() == 1
    assert Notification.objects.get().user is not editor
