import pytest
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management import CommandError, call_command

from grandchallenge.challenges.models import Challenge
from grandchallenge.pages.models import Page
from tests.factories import (
    ChallengeFactory,
    ImagingModalityFactory,
    PageFactory,
)


@pytest.mark.django_db
def test_copy_challenge():
    with pytest.raises(CommandError) as e:
        call_command("copy_challenge")
    assert "the following arguments are required: source, dest" in str(e.value)

    with pytest.raises(CommandError) as e:
        call_command("copy_challenge", "foo")
    assert "the following arguments are required: dest" in str(e.value)

    with pytest.raises(ObjectDoesNotExist):
        call_command("copy_challenge", "foo", "bar")
    site = Site.objects.get_current()
    site.domain = "foo.bar"
    site.save()
    src = ChallengeFactory(short_name="foo", use_evaluation=True)
    # toggle a boolean field
    phase = src.phase_set.get()
    phase.show_supplementary_url = not phase.show_supplementary_url
    phase.save()

    src.modalities.add(ImagingModalityFactory())

    for _ in range(3):
        PageFactory(
            challenge=src,
            html=(
                "<p><a href='https://foo.foo.bar/test'>test1</a>"
                '<a href="https://foo.foo.bar/test">test2</a>'
                "<a href='http://foo.foo.bar/test'>test3</a>"
                '<a href="http://foo.foo.bar/test">test4</a></p>'
            ),
        )

    assert Challenge.objects.count() == 1
    assert Page.objects.count() == 4

    with pytest.raises(CommandError):
        call_command("copy_challenge", "foo", "fOo")

    with pytest.raises(ValidationError):
        call_command("copy_challenge", "foo", "b_a_r")

    call_command("copy_challenge", "foo", "bar")

    assert Challenge.objects.count() == 2
    assert Page.objects.count() == 8

    dest = Challenge.objects.get(short_name="bar")

    for page in dest.page_set.exclude(title="foo"):
        assert page.html == (
            '<p><a href="https://bar.foo.bar/test">test1</a>'
            '<a href="https://bar.foo.bar/test">test2</a>'
            '<a href="https://bar.foo.bar/test">test3</a>'
            '<a href="https://bar.foo.bar/test">test4</a></p>'
        )

    assert (
        dest.phase_set.get().show_supplementary_url
        == src.phase_set.get().show_supplementary_url
    )
    assert {*dest.modalities.all()} == {*src.modalities.all()}
    assert {*dest.get_admins()} == {*src.get_admins()}

    with pytest.raises(ValidationError):
        call_command("copy_challenge", "foo", "bAr")
