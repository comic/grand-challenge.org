import json

import pytest
from django.core.files.base import ContentFile
from guardian.shortcuts import assign_perm

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import SubmissionFactory
from tests.factories import (
    ImageFileFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


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
            f"{settings.PROTECTED_S3_STORAGE_KWARGS['endpoint_url']}/"
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
def test_output_download(client):
    """Only viewers of the job should be allowed to download result files."""
    user1, user2 = UserFactory(), UserFactory()
    job = AlgorithmJobFactory(creator=user1)

    detection_interface = ComponentInterface(
        store_in_database=False,
        relative_path="detection_results.json",
        slug="detection-results",
        title="Detection Results",
        kind=ComponentInterface.Kind.ANY,
    )
    detection_interface.save()
    job.algorithm_image.algorithm.outputs.add(detection_interface)

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
    job.outputs.add(output_civ)

    tests = [
        (403, None),
        (302, user1),
        (403, user2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=job.outputs.first().file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]
