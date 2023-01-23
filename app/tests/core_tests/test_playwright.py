import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright


class MyViewTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        #  you are certain there is no chance of your code being run
        #  concurrently, and you absolutely need to run your sync code from an
        #  async context, then you can disable the warning by setting the
        #  DJANGO_ALLOW_ASYNC_UNSAFE environment variable to any value.
        #
        # Warning
        #
        # If you enable this option and there is concurrent access to the
        # async-unsafe parts of Django, you may suffer data loss or corruption.
        # Be very careful and do not use this in production environments.
        # TODO ensure we are definitely not running concurrently
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        super().setUpClass()

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.browser.close()
        cls.playwright.stop()

    def test_login(self):
        page = self.browser.new_page()
        page.goto(f"{self.live_server_url}/django-admin/")
        page.wait_for_selector("text=Please sign in")
        page.fill("[name=login]", "myuser")
        page.fill("[name=password]", "secret")
        page.click("text=Sign In")
        # TODO test doesn't actually test anything
        # assert len(page.eval_on_selector(".errornote", "el => el.innerText")) > 0
        page.close()
