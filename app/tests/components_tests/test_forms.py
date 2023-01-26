import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.models import ComponentInterface
from grandchallenge.uploads.models import UserUpload
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_interface_form_field_image_queryset_filter():
    user = UserFactory()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    upload1 = UserUploadFactory(creator=user)
    upload2 = UserUploadFactory()
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    field = InterfaceFormField(instance=ci, user=user)
    assert im1 in field.field.fields[0].queryset.all()
    assert im2 not in field.field.fields[0].queryset.all()
    assert upload1 in field.field.fields[1].queryset.all()
    assert upload2 not in field.field.fields[1].queryset.all()
