import uuid

import pytest
from django.template import Template, Context, RequestContext
from django.test import RequestFactory, override_settings

from tests.factories import ChallengeFactory, PageFactory


@pytest.mark.django_db
def test_taglist():
    template = Template(
        "{% load taglist from grandchallenge_tags %}{% taglist %}"
    )
    rendered = template.render(Context({}))
    assert "<td>listdir</td>" in rendered
    assert "<td>get_project_prefix</td>" in rendered


@pytest.mark.django_db
def test_allusers_statistics():
    c = ChallengeFactory(short_name=str(uuid.uuid4()))
    p = PageFactory(challenge=c)
    template = Template(
        "{% load allusers_statistics from grandchallenge_tags %}"
        "{% allusers_statistics %}"
    )
    context = Context({"currentpage": p})
    rendered = template.render(context)
    assert "['Country', '#Participants']" in rendered


@pytest.mark.django_db
def test_project_statistics():
    c = ChallengeFactory(short_name=str(uuid.uuid4()))
    p = PageFactory(challenge=c)
    template = Template(
        "{% load project_statistics from grandchallenge_tags %}"
        "{% project_statistics %}"
    )
    context = Context({"currentpage": p})
    rendered = template.render(context)
    assert "Number of users: 0" in rendered
    assert "['Country', '#Participants']" in rendered


@pytest.mark.django_db
def test_url_parameter(rf: RequestFactory):
    r = rf.get("/who?me=john")
    template = Template(
        "{% load url_parameter from grandchallenge_tags %}"
        "{% url_parameter me %}"
    )
    context = RequestContext(request=r)
    rendered = template.render(context)
    assert rendered == "john"


@pytest.mark.django_db
@pytest.mark.parametrize("view_type", ["anode09", "anode09_table"])
@override_settings(MEDIA_ROOT="/app/tests/core_tests/resources/")
def test_insert_graph(rf: RequestFactory, view_type):
    c = ChallengeFactory(short_name="testproj1734621")
    p = PageFactory(challenge=c)
    r = rf.get("/Result/?id=4")
    template = Template(
        "{% load insert_graph from grandchallenge_tags %}"
        "{% insert_graph 4.php type:"
        f"{view_type}"
        " %}"
    )
    context = RequestContext(r, {"currentpage": p})
    rendered = template.render(context)
    assert "pageError" not in rendered
    assert "Error rendering graph from file" not in rendered
    if view_type == "anode09":
        assert "Created with matplotlib" in rendered
    else:
        assert "comictablecontainer" in rendered


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/app/tests/core_tests/resources/")
def test_image_browser(rf: RequestFactory):
    c = ChallengeFactory(short_name="testproj-image-browser")
    p = PageFactory(challenge=c)
    template = Template(
        "{% load image_browser from grandchallenge_tags %}"
        "{% image_browser path:public_html "
        "config:public_html/promise12_viewer_config_new.js %}"
    )
    context = RequestContext(
        rf.get("/results/?id=CBA&folder=20120627202920_304_CBA_Results"),
        {"currentpage": p},
    )
    context.update({"site": c})
    rendered = template.render(context)
    assert "pageError" not in rendered
    assert "Error rendering Visualization" not in rendered
    assert "20120627202920_304_CBA_Results" in rendered
    assert "Results viewer" in rendered
