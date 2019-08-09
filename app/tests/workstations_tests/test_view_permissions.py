import pytest
from django.conf import settings

from tests.factories import (
    WorkstationFactory,
    WorkstationImageFactory,
    SessionFactory,
)
from tests.utils import validate_staff_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "workstations:list",
        "workstations:update",
        "workstations:image-create",
        "workstations:image-detail",
        "workstations:image-update",
        "workstations:session-create",
        "workstations:session-update",
    ],
)
def test_workstations_staff_views(client, view):
    if view in [
        "workstations:update",
        "workstations:image-create",
        "workstations:session-create",
    ]:
        reverse_kwargs = {"slug": WorkstationFactory().slug}
    elif view in ["workstations:image-detail", "workstations:image-update"]:
        wsi = WorkstationImageFactory()
        reverse_kwargs = {"slug": wsi.workstation.slug, "pk": wsi.pk}
    elif view in [
        "workstations:session-detail",
        "workstations:session-update",
    ]:
        session = SessionFactory()
        reverse_kwargs = {
            "slug": session.workstation_image.workstation.slug,
            "pk": session.pk,
        }
    else:
        reverse_kwargs = {}

    validate_staff_only_view(
        client=client, viewname=view, reverse_kwargs=reverse_kwargs
    )


@pytest.mark.django_db
def test_session_redirect_staff_only(client):
    # Create the default image
    WorkstationImageFactory(
        workstation__title=settings.DEFAULT_WORKSTATION_SLUG, ready=True
    )
    wsi = WorkstationImageFactory(ready=True)

    # Validate
    validate_staff_only_view(
        client=client,
        viewname="workstations:default-session-redirect",
        reverse_kwargs={},
        should_redirect=True,
    )
    validate_staff_only_view(
        client=client,
        viewname="workstations:workstation-session-redirect",
        reverse_kwargs={"slug": wsi.workstation.slug},
        should_redirect=True,
    )
    validate_staff_only_view(
        client=client,
        viewname="workstations:workstation-image-session-redirect",
        reverse_kwargs={"slug": wsi.workstation.slug, "pk": wsi.pk},
        should_redirect=True,
    )
