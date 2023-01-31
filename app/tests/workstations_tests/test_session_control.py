import json
from pathlib import Path

import pytest
from django.conf import settings
from django.views.generic import TemplateView

import tests.settings as test_settings
from tests.utils import playwright_trace


class SessionControlView(TemplateView):
    url_route = "session-control/"
    template_name = "session_control.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        context.update(
            {"domain": test_settings.DJANGO_LIVE_TEST_SERVER_ADDRESS}
        )
        return context


class WorkstationView(TemplateView):
    url_route = "workstation/"
    template_name = "workstation.html"


class SessionCreationView(TemplateView):
    url_route = "new-session/"
    template_name = "new_session.html"


@pytest.mark.playwright
def test_viewer_session_control(playwright_live_server, page):
    with playwright_trace(page.context, directory=Path("/app/test_results")):
        url = playwright_live_server
        session_create_view = (
            f"{url.scheme}://{url.netloc}/{SessionCreationView.url_route}"
        )
        session_control_view = (
            f"{url.scheme}://{url.netloc}/{SessionControlView.url_route}"
        )
        subdomain = settings.WORKSTATIONS_ACTIVE_REGIONS[0]
        mock_workstation_view = f"{url.scheme}://{subdomain}.{url.netloc}/{WorkstationView.url_route}"
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
