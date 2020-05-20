import pytest


@pytest.mark.django_db
def test_cleanup_scheduled_for_each_workstation_queue(settings):
    assert len(settings.WORKSTATIONS_ACTIVE_REGIONS) > 0

    for region in settings.WORKSTATIONS_ACTIVE_REGIONS:
        job = settings.CELERY_BEAT_SCHEDULE[f"stop_expired_services_{region}"]
        assert job["options"]["queue"] == f"workstations-{region}"
        assert job["kwargs"]["region"] == region
