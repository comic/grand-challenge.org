import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.test.client import RequestFactory

from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets.uploader import (
    AjaxUploadWidget,
    UploadedAjaxFileList,
)
from tests.factories import UserFactory
from tests.jqfileupload_tests.utils import (
    create_upload_file_request,
    load_test_data,
    generate_new_upload_id,
)


@pytest.mark.django_db
def test_render():
    user = UserFactory()

    widget = AjaxUploadWidget(multifile=True, user=user)
    render_result = widget.render("some_name", None)
    assert isinstance(render_result, str)

    render_result = widget.render("some_name", (uuid.uuid4(), uuid.uuid4()))
    assert isinstance(render_result, str)

    widget = AjaxUploadWidget(multifile=False, user=user)
    render_result = widget.render("some_name", None)
    assert isinstance(render_result, str)

    render_result = widget.render("some_name", (uuid.uuid4(), uuid.uuid4()))
    assert isinstance(render_result, str)


def test_form_field_to_python():
    form_field = UploadedAjaxFileList()
    uuid_string = ",".join(
        (
            "4dec34db-930f-48be-bb65-d7f8319ff654",
            "5d901b2c-7cd1-416e-9952-d30b6a0edcba",
            "4a3c5731-0050-4489-8364-282278f7190f",
        )
    )
    staged_files = form_field.to_python(uuid_string)
    assert ",".join(str(sf.uuid) for sf in staged_files) == uuid_string
    with pytest.raises(ValidationError):
        form_field.to_python("asdfasdfsdafasdf")
    other_string = uuid_string[10:]
    with pytest.raises(ValidationError):
        form_field.to_python(other_string)


def test_form_field_prepare_value_not_implemented():
    form_field = UploadedAjaxFileList()
    assert form_field.prepare_value("") is None


@pytest.mark.django_db
def test_upload_validator_using_wrong_extension(rf: RequestFactory):
    widget = AjaxUploadWidget(
        upload_validators=[
            ExtensionValidator(allowed_extensions=(".allowed-extension",))
        ]
    )
    content = load_test_data()

    upload_id = generate_new_upload_id(
        test_upload_validator_using_wrong_extension, content
    )

    request = create_upload_file_request(
        rf, content=b"should error", filename="test.wrong_extension"
    )
    response = widget.handle_ajax(request)
    assert response.status_code == 403

    request = create_upload_file_request(
        rf, content=b"should error", filename="test.allowed-extension"
    )
    response = widget.handle_ajax(request)
    assert response.status_code == 200
