import pytest
from django.utils.encoding import force_text


@pytest.mark.django_db
def test_result_list_html(client):
    response = client.get('/evaluation/api/v1/results/',
                          HTTP_ACCEPT='text/html')
    assert "Result List" in force_text(response.content)
