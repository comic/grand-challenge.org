import json

import pytest
from django.urls import path
from django.views.generic import TemplateView

from config.urls.root import urlpatterns


class SessionControlTestView(TemplateView):
    template_name = "playwright.html"


class AcknowledgeMessageView(TemplateView):
    template_name = "ack_message.html"


class NewSessionWindowView(TemplateView):
    template_name = "new_session.html"


urlpatterns = [
    path("session-control/", SessionControlTestView.as_view()),
    path("ack-message/", AcknowledgeMessageView.as_view()),
    path("new-session/", NewSessionWindowView.as_view()),
] + urlpatterns


@pytest.mark.urls(__name__)
@pytest.mark.playwright
def test_viewer_session_control(live_server, page):
    page.goto(f"{live_server}/session-control/")
    # Test if a fresh click opens up a new page
    with page.expect_popup() as viewer_page_info:
        page.get_by_role("button", name="Launch new Session").click()
        viewer_page = viewer_page_info.value
    viewer_page.get_by_text("New session").wait_for()
    assert viewer_page.url.startswith(f"{live_server}/new-session/")

    # Setup mock acknowledge
    viewer_page.goto(f"{live_server}/ack-message")
    viewer_page.evaluate("enableMockAcks()")

    # Test if pressing launch indeed sends a session control message
    page.get_by_role("button", name="Launch new Session").click()
    received_msg = json.loads(
        viewer_page.locator("#messages :nth-child(1)").inner_text()
    )
    assert "id" in received_msg["sessionControl"]["header"]
    assert viewer_page.url.startswith(f"{live_server}")

    # check that ack message is returned
    sent_msg = json.loads(
        viewer_page.locator("#acks :nth-child(1)").inner_text()
    )
    assert "acknowledge" in sent_msg["sessionControl"]["header"]

    # Test that if acknowledge sent too late, a new session will be created
    viewer_page.evaluate("enableMockAcksWithDelay()")
    page.get_by_role("button", name="Launch new Session").click()
    viewer_page.get_by_text("New session").wait_for()
    assert viewer_page.url.startswith("http://localhost:9200/new-session/")

    # Test if disabling the acknowledgment will result in a new session being created
    viewer_page.goto(f"{live_server}/ack-message")
    viewer_page.evaluate("disableMockAcks()")
    page.get_by_role("button", name="Launch new Session").click()
    viewer_page.get_by_text("New session").wait_for()
    assert viewer_page.url.startswith("http://localhost:9200/new-session/")

    # Clean up
    page.close()
