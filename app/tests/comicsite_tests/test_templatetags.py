import uuid

import pytest
from django.template import Template, Context, RequestContext
from django.test import RequestFactory, override_settings

from tests.factories import ChallengeFactory, PageFactory


@pytest.mark.django_db
def test_taglist():
    template = Template(
        '{% load taglist from comic_templatetags %}{% taglist %}'
    )

    rendered = template.render(Context({}))

    assert '<td>listdir</td>' in rendered
    assert '<td>get_project_prefix</td>' in rendered


@pytest.mark.django_db
# Override the settings so we can use the test file in dataproviders
@override_settings(MEDIA_ROOT='/app/tests/dataproviders_tests/')
@override_settings(MAIN_PROJECT_NAME='resources')
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
    c = ChallengeFactory(short_name=str(uuid.uuid4()))
    p = PageFactory(challenge=c)

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
    c = ChallengeFactory(short_name=str(uuid.uuid4()))
    p = PageFactory(challenge=c)

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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view_type",
    [
        'anode09',
        'anode09_table',
    ]
)
@override_settings(MEDIA_ROOT='/app/tests/comicsite_tests/resources/')
def test_insert_graph(rf: RequestFactory, view_type):
    c = ChallengeFactory(short_name='testproj1734621')
    p = PageFactory(challenge=c)

    r = rf.get('/Result/?id=4')

    template = Template(
        '{% load insert_graph from comic_templatetags %}'
        '{% insert_graph 4.php type:'
        f'{view_type}'
        ' %}'
    )

    context = RequestContext(request=r)
    context.page = p

    rendered = template.render(context)

    assert "pageError" not in rendered
    assert "Error rendering graph from file" not in rendered
    if view_type == 'anode09':
        assert "Created with matplotlib" in rendered
    else:
        assert "comictablecontainer" in rendered


@pytest.mark.django_db
@override_settings(MEDIA_ROOT='/app/tests/comicsite_tests/resources/')
def test_image_browser(rf: RequestFactory):
    c = ChallengeFactory(short_name='testproj-image-browser')
    p = PageFactory(challenge=c)

    template = Template(
        '{% load image_browser from comic_templatetags %}'
        '{% image_browser path:public_html '
        'config:public_html/promise12_viewer_config_new.js %}'
    )

    context = RequestContext(request=rf.get(
        '/results/?id=CBA&folder=20120627202920_304_CBA_Results'
    ))
    context.page = p
    context.update({'site': c})

    rendered = template.render(context)

    assert "pageError" not in rendered
    assert "Error rendering Visualization" not in rendered
    assert "20120627202920_304_CBA_Results" in rendered
    assert "Results viewer" in rendered
