import json
import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.views.generic import TemplateView
from playwright.sync_api import sync_playwright


class SessionControlView(TemplateView):
    template_name = "session_control.html"


class WorkstationView(TemplateView):
    template_name = "workstation.html"


class SessionCreationView(TemplateView):
    template_name = "new_session.html"


class PlaywrightTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # See https://github.com/microsoft/playwright-pytest/issues/29
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        super().setUpClass()

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.browser.close()
        cls.playwright.stop()

        del os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"]

    def test_viewer_session_control(self):
        with self.settings(
            WORKSTATIONS_EXTRA_BROADCAST_DOMAINS=[self.live_server_url],
        ):
            page = self.browser.new_page()

            session_create_view = (
                f"{self.live_server_url}{reverse('new-session-test')}"
            )
            session_control_view = (
                f"{self.live_server_url}{reverse('session-control-test')}"
            )
            mock_workstation_view = (
                f"{self.live_server_url}{reverse('workstation-mock')}"
            )
            page.goto(session_control_view)

            # Test if a fresh click opens up a new page
            with page.expect_popup() as viewer_page_info:
                page.get_by_role("button", name="Launch new Session").click()
                viewer_page = viewer_page_info.value
            viewer_page.get_by_text(
                SessionCreationView.template_name
            ).wait_for()

            # Setup mock acknowledge
            viewer_page.goto(mock_workstation_view)
            viewer_page.evaluate("enableMockAcks()")

            # Test if pressing launch indeed sends a session control message
            page.get_by_role("button", name="Launch new Session").click()
            received_msg = json.loads(
                viewer_page.locator("#messages :nth-child(1)").inner_text()
            )
            assert "id" in received_msg["sessionControl"]["meta"]

            # check that ack message is returned
            sent_msg = json.loads(
                viewer_page.locator("#acks :nth-child(1)").inner_text()
            )
            assert "acknowledge" in sent_msg["sessionControl"]["meta"]

            # check that an ack with the wrong id is ignored
            viewer_page.goto(mock_workstation_view)
            viewer_page.evaluate("enableIncorrectMockAck()")
            page.get_by_role("button", name="Launch new Session").click()
            received_msg2 = json.loads(
                viewer_page.locator("#messages :nth-child(1)").inner_text()
            )
            sent_msg2 = json.loads(
                viewer_page.locator("#acks :nth-child(1)").inner_text()
            )
            assert (
                received_msg2["sessionControl"]["meta"]["id"]
                != sent_msg2["sessionControl"]["meta"]["acknowledge"]["id"]
            )
            viewer_page.get_by_text(
                SessionCreationView.template_name
            ).wait_for()
            assert viewer_page.url.startswith(session_create_view)

            # Set timeout to 0, test that a new session will be created
            viewer_page.goto(mock_workstation_view)
            page.get_by_role("button", name="Test timeout").click()
            viewer_page.get_by_text(
                SessionCreationView.template_name
            ).wait_for()
            assert viewer_page.url.startswith(session_create_view)

            # Test if disabling the acknowledgment will result in a new session being created
            viewer_page.goto(mock_workstation_view)
            viewer_page.evaluate("disableMockAcks()")
            page.get_by_role("button", name="Launch new Session").click()
            viewer_page.get_by_text(
                SessionCreationView.template_name
            ).wait_for()
            assert viewer_page.url.startswith(session_create_view)

            # Clean up
            page.close()
