import json
import pytest
from django.utils.encoding import force_text


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_input, expected",
    [("results", "Result List"),
     ("submissions", "Submission List"),
     ("jobs", "Job List"),
     ("methods", "Method List")]
)
def test_result_list(client, test_input, expected):
    # Check for the correct HTML view
    response = client.get('/evaluation/api/v1/%s/' % test_input,
                          HTTP_ACCEPT='text/html')
    assert expected in force_text(response.content)
    assert response.status_code == 200

    # There should be no content, but we should be able to do json.loads
    response = client.get('/evaluation/api/v1/%s/' % test_input,
                          HTTP_ACCEPT='application/json')
    assert response.status_code == 200
    assert not json.loads(response.content)
