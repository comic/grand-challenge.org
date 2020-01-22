import pytest
from django.core.management import call_command

from tests.factories import PageFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "html_in,html_out",
    (
        (
            "/site/myChallenge-18/serve/whatever/foo.pdf",
            "/media/myChallenge-18/whatever/foo.pdf",
        ),
        (
            "/site/myChallenge-18/whatever/foo.pdf",
            "/site/myChallenge-18/whatever/foo.pdf",
        ),
        ("/site/myChallenge-18/serve", "/site/myChallenge-18/serve",),
        (
            "/site/myChallenge-18/serve/whatever/foo.pdf \n\n jdsagflk/site/myChallenge-18/serve/gasd/bar.pdf",
            "/media/myChallenge-18/whatever/foo.pdf \n\n jdsagflk/media/myChallenge-18/gasd/bar.pdf",
        ),
        (
            "/site/myChallenge-18/serve/whatever/foo.pdf/site/myChallenge-18/serve/whatever/foo.pdf",
            "/media/myChallenge-18/whatever/foo.pdf/media/myChallenge-18/whatever/foo.pdf",
        ),
    ),
)
def test_site_serve_rewrite(html_in, html_out):
    p = PageFactory(html=html_in)

    call_command("update_media_links")

    p.refresh_from_db()
    assert p.html == html_out
