import pytest
from django.template import Template, Context, RequestContext
from django.test import RequestFactory

from tests.factories import ChallengeFactory, PageFactory


@pytest.mark.django_db
def test_taglist():
    template = Template(
        '{% load taglist from comic_templatetags %}{% taglist %}'
    )

    rendered = template.render(Context({}))

    assert '<td>listdir</td>' in rendered
    assert '<td>get_result_info</td>' in rendered
    assert '<td>get_project_prefix</td>' in rendered


@pytest.mark.django_db
def test_all_projectlinks():
    c = ChallengeFactory(hidden=False)
    hidden = ChallengeFactory(hidden=True)

    template = Template(
        '{% load all_projectlinks from comic_templatetags %}'
        '{% all_projectlinks %}'
    )

    rendered = template.render(Context({}))

    assert c.short_name in rendered
    assert hidden.short_name not in rendered


@pytest.mark.django_db
def test_allusers_statistics():
    p = PageFactory()

    template = Template(
        '{% load allusers_statistics from comic_templatetags %}'
        '{% allusers_statistics %}'
    )

    context = Context()
    context.page = p

    rendered = template.render(context)

    assert "['Country', '#Participants']" in rendered


@pytest.mark.django_db
def test_project_statistics():
    p = PageFactory()

    template = Template(
        '{% load project_statistics from comic_templatetags %}'
        '{% project_statistics %}'
    )

    context = Context()
    context.page = p

    rendered = template.render(context)

    assert 'Number of users: 0' in rendered
    assert "['Country', '#Participants']" in rendered


@pytest.mark.django_db
def test_url_parameter(rf: RequestFactory):
    r = rf.get('/who?me=john')

    template = Template(
        '{% load url_parameter from comic_templatetags %}'
        '{% url_parameter me %}'
    )

    context = RequestContext(request=r)

    rendered = template.render(context)

    assert rendered == 'john'

# {% image_browser path:string - path relative to current project
#                  config:string - path relative to current project %}

# get_result_info

# insert_graph
