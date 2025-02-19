import json
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from guardian.shortcuts import assign_perm

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from tests.algorithms_tests.factories import (
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests import RESOURCE_PATH
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    SubmissionFactory,
)
from tests.factories import (
    ChallengeRequestFactory,
    GroupFactory,
    ImageFileFactory,
    UserFactory,
)
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.utils import get_view_for_user
from tests.workstations_tests.factories import FeedbackFactory


@pytest.mark.django_db
@pytest.mark.parametrize("cloudfront", (True, False))
def test_image_response(client, settings, cloudfront, tmpdir):
    settings.CLOUDFRONT_PRIVATE_KEY_BASE64 = (
        "LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlDWFFJQkFBS0JnUURBN2tp"
        "OWdJL2xSeWdJb09qVjF5eW1neDZGWUZsekorejFBVE1hTG81N25MNTdBYXZXCmhiNjhI"
        "WVk4RUEwR0pVOXhRZE1WYUhCb2dGM2VpQ1dZWFNVWkNXTS8rTTUrWmNkUXJhUlJTY3Vj"
        "bW42ZzRFdlkKMks0VzJweGJxSDh2bVVpa1B4aXI0MUVlQlBMak1Pekt2Ynp6UXk5ZS96"
        "eklRVlJFS1NwLzd5MW15d0lEQVFBQgpBb0dBQmM3bXA3WFlIeW51UFp4Q2hqV05KWklx"
        "K0E3M2dtMEFTRHY2QXQ3RjhWaTlyMHhVbFFlL3YwQVFTM3ljCk44UWx5UjRYTWJ6TUxZ"
        "azN5anhGRFhvNFpLUXRPR3pMR3RlQ1Uyc3JBTmlMdjI2L2ltWEE4RlZpZFpmdFRBdEwK"
        "dmlXUVpCVlBUZVlJQTY5QVRVWVBFcTBhNXU1d2pHeVVPaWo5T1d5dXkwMW1iUGtDUVFE"
        "bHVZb05wUE9la1EwWgpXclBnSjVyeGM4ZjZ6RzM3WlZvREJpZXhxdFZTaElGNVczeFl1"
        "V2hXNWtZYjBobGlZZmtxMTVjUzd0OW05NWgzCjFRSmYveEkvQWtFQTF2OWwvV04xYTFO"
        "M3JPSzRWR29Db2t4N2tSMlN5VE1TYlpnRjlJV0pOT3VnUi9XWnc3SFQKbmppcE8zYzlk"
        "eTFNczlwVUt3VUY0NmQ3MDQ5Y2s4SHdkUUpBUmdyU0t1TFdYTXlCSCsvbDFEeC9JNHRY"
        "dUFKSQpybFB5bytWbWlPYzdiNU56SHB0a1NIRVBmUjlzMU9LMFZxamtuY2xxQ0ozSWc4"
        "Nk9NRXRFRkJ6alpRSkJBS1l6CjQ3MGhjUGthR2s3dEtZQWdQNDhGdnhSc256ZW9vcHRV"
        "Ulc1RStNK1BRMlc5aURQUE9YOTczOStYaTAyaEdFV0YKQjBJR2JRb1RSRmRFNFZWY1BL"
        "MENRUUNlUzg0bE9EbEMwWTJCWnYySnhXM09zdi9Xa1VRNGRzbGZBUWwxVDMwMwo3dXd3"
        "cjdYVHJvTXY4ZElGUUlQcmVvUGhSS21kL1NiSnpiaUtmUy80UURoVQotLS0tLUVORCBS"
        "U0EgUFJJVkFURSBLRVktLS0tLQo="
    )
    settings.CLOUDFRONT_KEY_PAIR_ID = "PK123456789754"
    settings.PROTECTED_S3_STORAGE_USE_CLOUDFRONT = cloudfront

    image_file = ImageFileFactory()
    user = UserFactory()

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    # Forbidden view
    assert response.status_code == 403
    assert not response.has_header("x-accel-redirect")

    assign_perm("view_image", user, image_file.image)

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    assert response.status_code == 302
    assert not response.has_header("x-accel-redirect")

    redirect = response.url

    if cloudfront:
        assert redirect.startswith(
            f"https://{settings.PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}/"
        )

        assert "AWSAccessKeyId" not in redirect
        assert "Signature" in redirect
        assert "Expires" in redirect
    else:
        assert redirect.startswith(
            f"{settings.AWS_S3_ENDPOINT_URL}/"
            f"{settings.PROTECTED_S3_STORAGE_KWARGS['bucket_name']}/"
        )

        assert "AWSAccessKeyId" in redirect
        assert "Signature" in redirect
        assert "Expires" in redirect


@pytest.mark.django_db
def test_submission_download(client, two_challenge_sets):
    """Only the challenge admin should be able to download submissions."""
    submission = SubmissionFactory(
        phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        creator=two_challenge_sets.challenge_set_1.participant,
    )

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   user
        # )
        (403, None),
        (403, two_challenge_sets.challenge_set_1.non_participant),
        (302, two_challenge_sets.challenge_set_1.participant),
        (403, two_challenge_sets.challenge_set_1.participant1),
        (302, two_challenge_sets.challenge_set_1.creator),
        (302, two_challenge_sets.challenge_set_1.admin),
        (403, two_challenge_sets.challenge_set_2.non_participant),
        (403, two_challenge_sets.challenge_set_2.participant),
        (403, two_challenge_sets.challenge_set_2.participant1),
        (403, two_challenge_sets.challenge_set_2.creator),
        (403, two_challenge_sets.challenge_set_2.admin),
        (302, two_challenge_sets.admin12),
        (403, two_challenge_sets.participant12),
        (302, two_challenge_sets.admin1participant2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=submission.predictions_file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]


@pytest.mark.django_db
def test_civ_file_download(client):
    """Only viewers of the job should be allowed to download result files."""
    detection_interface = ComponentInterface(
        store_in_database=False,
        relative_path="detection_results.json",
        slug="detection-results",
        title="Detection Results",
        kind=ComponentInterface.Kind.ANY,
    )
    detection_interface.save()
    output_civ = ComponentInterfaceValue.objects.create(
        interface=detection_interface
    )
    detection = {
        "detected points": [
            {"type": "Point", "start": [0, 1, 2], "end": [3, 4, 5]}
        ]
    }
    output_civ.file.save(
        "detection_results.json",
        ContentFile(
            bytes(json.dumps(detection, ensure_ascii=True, indent=2), "utf-8")
        ),
    )
    user1, user2 = UserFactory(), UserFactory()

    def has_correct_access(user_allowed, user_denied, url):
        tests = [(403, None), (302, user_allowed), (403, user_denied)]

        for test in tests:
            response = get_view_for_user(url=url, client=client, user=test[1])
            assert response.status_code == test[0]

    # test algorithm
    job = AlgorithmJobFactory(creator=user1, time_limit=60)
    interface = AlgorithmInterfaceFactory(outputs=[detection_interface])
    job.algorithm_image.algorithm.interfaces.add(interface)
    job.outputs.add(output_civ)

    has_correct_access(user1, user2, job.outputs.first().file.url)
    job.outputs.remove(output_civ)

    # test evaluation
    evaluation = EvaluationFactory(time_limit=60)
    evaluation.output_interfaces.add(detection_interface)
    evaluation.outputs.add(output_civ)

    group = GroupFactory()
    group.user_set.add(user1)
    assign_perm("view_evaluation", group, evaluation)

    # Evaluation inputs and outputs should always be denied
    assert (
        get_view_for_user(
            url=evaluation.outputs.first().file.url, client=client, user=None
        ).status_code
        == 403
    )
    assert (
        get_view_for_user(
            url=evaluation.outputs.first().file.url, client=client, user=user1
        ).status_code
        == 403
    )
    assert (
        get_view_for_user(
            url=evaluation.outputs.first().file.url, client=client, user=user2
        ).status_code
        == 403
    )
    evaluation.outputs.remove(output_civ)

    # test archive
    archive = ArchiveFactory()
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.add(output_civ)
    archive.add_editor(user1)
    has_correct_access(user1, user2, archive_item.values.first().file.url)
    archive.remove_editor(user1)
    archive.add_user(user1)
    has_correct_access(user1, user2, archive_item.values.first().file.url)
    archive.remove_user(user1)

    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(output_civ)
    rs.add_editor(user1)
    has_correct_access(user1, user2, ds.values.first().file.url)
    rs.remove_editor(user1)
    rs.add_reader(user1)
    has_correct_access(user1, user2, ds.values.first().file.url)
    rs.remove_reader(user1)


@pytest.mark.django_db
def test_structured_challenge_submission_form_download(
    client, challenge_reviewer
):
    user = UserFactory()
    challenge_request = ChallengeRequestFactory()
    challenge_request.structured_challenge_submission_form.save(
        "test.pdf", ContentFile(b"foo,\nbar,\n")
    )

    tests = [
        (403, None),
        (403, user),
        (302, challenge_request.creator),
        (302, challenge_reviewer),
    ]

    for test in tests:
        response = get_view_for_user(
            url=challenge_request.structured_challenge_submission_form.url,
            client=client,
            user=test[1],
        )
        assert response.status_code == test[0]


@pytest.mark.django_db
def test_session_feedback_screenshot_download(client):
    """Only staff users should be able to download the screenshot."""
    user = UserFactory()
    staff = UserFactory(is_staff=True)
    feedback = FeedbackFactory(
        screenshot=ImageFile(
            open(Path(RESOURCE_PATH / "test_grayscale.jpg"), "rb")
        )
    )

    tests = [
        (403, None),
        (403, user),
        (403, feedback.session.creator),
        (302, staff),
    ]

    for test in tests:
        response = get_view_for_user(
            url=feedback.screenshot.url,
            client=client,
            user=test[1],
        )
        assert response.status_code == test[0]
