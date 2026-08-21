import pytest

from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmLambdaChoices,
)
from grandchallenge.reader_studies.models import QuestionWidgetKindChoices
from grandchallenge.reader_studies.serializers import QuestionSerializer
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_widget_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["widget"] == ""
    qu.widget = QuestionWidgetKindChoices.ACCEPT_REJECT
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert (
        serializer2.data["widget"]
        == QuestionWidgetKindChoices.ACCEPT_REJECT.label
    )


@pytest.mark.django_db
def test_interactive_algorithm_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["interactive_algorithms"] == []
    qu.interactive_algorithm = InteractiveAlgorithmLambdaChoices.ULS23_BASELINE
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer2.data["interactive_algorithms"] == ["uls23-baseline"]


@pytest.mark.django_db
def test_default_annotation_color_on_question_serializer(rf):
    qu = QuestionFactory()

    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["default_annotation_color"] == ""

    qu.default_annotation_color = "#000000"
    qu.save()

    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer2.data["default_annotation_color"] == "#000000"


@pytest.mark.parametrize(
    "markdown_field,rendered_field",
    (
        ("help_text_markdown", "help_text_safe"),
        ("end_of_study_text_markdown", "end_of_study_text_safe"),
    ),
)
@pytest.mark.django_db
def test_markdown_is_scrubbed(client, markdown_field, rendered_field):
    rs = ReaderStudyFactory(
        **{
            markdown_field: "# Here come some naughty strings\n\n"
            "<a href='javascript:alert(1)' onmouseover='alert(1)'>Click me</a>"
            "<script>alert('XSS')</script>"
        }
    )
    u = UserFactory()
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=rs.api_url, user=u)
    assert response.status_code == 200

    rendered_text = response.json()[rendered_field]
    assert (
        rendered_text
        == '<h1>Here come some naughty strings</h1>\n<p><a rel="noopener" target="_blank">Click me</a></p>'
    )


@pytest.mark.django_db
def test_reader_study_title_tags_scrubbed(client):
    rs = ReaderStudyFactory(
        title="<b>No tags allowed</b><script>alert('XSS')</script>"
    )
    u = UserFactory()
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=rs.api_url, user=u)
    assert response.status_code == 200

    rendered_text = response.json()["title_safe"]
    assert rendered_text == "No tags allowed"


@pytest.mark.django_db
def test_display_set_title_tags_scrubbed(client):
    ds = DisplaySetFactory(
        title="<b>No tags allowed</b><script>alert('XSS')</script>"
    )
    u = UserFactory()
    ds.reader_study.add_reader(u)

    response = get_view_for_user(client=client, url=ds.api_url, user=u)
    assert response.status_code == 200

    rendered_text = response.json()["title_safe"]
    assert rendered_text == "No tags allowed"


@pytest.mark.django_db
def test_display_view_content_scrubbed(client):
    image = ImageFactory(name="display-image")
    image2 = ImageFactory(name="display-image-2")
    rs = ReaderStudyFactory(
        case_text={
            image.name: "<b>My Help Text</b><script>naughty</script>",
            image2.name: "<b>Another Help Text</b><script>naughty</script>",
            "not-an-image": "Should not appear",
        }
    )
    ds = DisplaySetFactory(reader_study=rs, title="empty")
    ds.values.add(ComponentInterfaceValueFactory(image=image))
    ds.values.add(ComponentInterfaceValueFactory(image=image2))

    # Ensure duplicate values do not duplicate output.
    ds.values.add(ComponentInterfaceValueFactory(image=image))

    u = UserFactory()
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=ds.api_url, user=u)
    assert response.status_code == 200

    rendered = response.json()
    assert (
        rendered["description"]
        == "<p><b>My Help Text</b></p><p><b>Another Help Text</b></p>"
    )
    assert rendered["descriptions_map_safe"] == {
        image.name: "<p><b>My Help Text</b></p>",
        image2.name: "<p><b>Another Help Text</b></p>",
    }


@pytest.mark.parametrize(
    "field_name",
    (
        "question_text",
        "empty_answer_confirmation_label",
    ),
)
@pytest.mark.django_db
def test_question_tags_scrubbed(client, field_name):
    q = QuestionFactory(
        **{field_name: "<b>No tags allowed</b><script>alert('XSS')</script>"},
    )
    u = UserFactory()
    q.reader_study.add_reader(u)

    response = get_view_for_user(client=client, url=q.api_url, user=u)
    assert response.status_code == 200

    rendered_text = response.json()[f"{field_name}_safe"]
    assert rendered_text == "No tags allowed"


@pytest.mark.django_db
def test_help_text_scrubbed(client):
    q = QuestionFactory(
        help_text="<b>some tags allowed</b><script>alert('XSS')</script>",
    )
    u = UserFactory()
    q.reader_study.add_reader(u)

    response = get_view_for_user(client=client, url=q.api_url, user=u)
    assert response.status_code == 200

    rendered_text = response.json()["help_text_safe"]
    assert rendered_text == "<b>some tags allowed</b>"
