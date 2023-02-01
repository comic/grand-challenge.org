import json
from pathlib import Path

import pytest
from django.conf import settings
from django.views.generic import TemplateView

from tests.utils import playwright_trace


class SessionControlView(TemplateView):
    template_name = "session_control.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        context.update(
            {
                "netloc": settings.DJANGO_LIVE_TEST_SERVER_ADDRESS,
                "domain": settings.DJANGO_LIVE_TEST_SERVER_ADDRESS.split(":")[
                    0
                ],
            }
        )
        return context


class WorkstationView(TemplateView):
    template_name = "workstation.html"


class SessionCreationView(TemplateView):
    template_name = "new_session.html"


@pytest.mark.playwright
def test_viewer_session_control(playwright_live_server, page, settings):
    with playwright_trace(page.context, directory=Path("/app/test_results")):
        url = playwright_live_server
        settings.DJANGO_LIVE_TEST_SERVER_ADDRESS = f"{url.netloc}"
        session_create_view = f"{url.scheme}://{url.netloc}/new-session/"
        session_control_view = f"{url.scheme}://{url.netloc}/session-control/"
        subdomain = settings.WORKSTATIONS_ACTIVE_REGIONS[0]
        mock_workstation_view = (
            f"{url.scheme}://{subdomain}.{url.netloc}/workstation/"
        )
        page.goto(session_control_view)

        # Test if a fresh click opens up a new page
        with page.expect_popup() as viewer_page_info:
            page.get_by_role("button", name="Launch new Session").click()
            viewer_page = viewer_page_info.value
        viewer_page.get_by_text(SessionCreationView.template_name).wait_for()

        # Setup mock acknowledge
        viewer_page.goto(mock_workstation_view)
        viewer_page.evaluate("enableMockAcks()")

        # Test if pressing launch indeed sends a session control message
        page.get_by_role("button", name="Launch new Session").click()
        received_msg = json.loads(
            viewer_page.locator("#messages :nth-child(1)").inner_text()
        )
        assert "id" in received_msg["sessionControl"]["header"]
        assert viewer_page.url.startswith(subdomain)

        # check that ack message is returned
        sent_msg = json.loads(
            viewer_page.locator("#acks :nth-child(1)").inner_text()
        )
        assert "acknowledge" in sent_msg["sessionControl"]["header"]

        # Test that if acknowledge sent too late, a new session will be created
        viewer_page.evaluate("enableMockAcksWithDelay()")
        page.get_by_role("button", name="Launch new Session").click()
        viewer_page.get_by_text(SessionCreationView.template_name).wait_for()
        assert viewer_page.url == session_create_view

        # Test if disabling the acknowledgment will result in a new session being created
        viewer_page.goto(mock_workstation_view)
        viewer_page.evaluate("disableMockAcks()")
        page.get_by_role("button", name="Launch new Session").click()

        viewer_page.get_by_text(SessionCreationView.template_name).wait_for()
        assert viewer_page.url == session_create_view

        # Clean up
        page.close()
