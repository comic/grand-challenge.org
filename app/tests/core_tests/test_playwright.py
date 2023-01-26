import pytest


@pytest.mark.playwright
def test_playwright(page, live_server):
    page.goto(f"{live_server}/django-admin/")
    page.wait_for_selector("text=Please sign in")
    page.fill("[name=login]", "myuser")
    page.fill("[name=password]", "secret")
    page.click("text=Sign In")
    # TODO test doesn't actually test anything
    # assert len(page.eval_on_selector(".errornote", "el => el.innerText")) > 0
    page.close()
