import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.emails.models import Email
from tests.emails_tests.factories import EmailFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_email_create(client):
    user = UserFactory()
    response = get_view_for_user(
        viewname="emails:create",
        client=client,
        method=client.post,
        data={"subject": "Test email", "body": "Some dummy content"},
        user=user,
    )
    assert response.status_code == 403
    assert Email.objects.count() == 0

    # only users with permission can create emails
    assign_perm("emails.add_email", user)
    response = get_view_for_user(
        viewname="emails:create",
        client=client,
        method=client.post,
        data={"subject": "Test email"},
        user=user,
    )
    assert response.status_code == 302
    assert Email.objects.count() == 1

    email = Email.objects.get()

    assert response.url == f"https://testserver/emails/{email.pk}/body-update/"
    assert email.subject == "Test email"


@pytest.mark.django_db
def test_email_metadata_update(client):
    user = UserFactory()
    email = EmailFactory(subject="Test email", body="Test content")
    response = get_view_for_user(
        viewname="emails:metadata-update",
        client=client,
        method=client.post,
        data={"subject": "Updated subject"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403

    # only users with permission can create emails
    assign_perm("emails.change_email", user)
    response = get_view_for_user(
        viewname="emails:metadata-update",
        client=client,
        method=client.post,
        data={"subject": "Updated subject"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 302
    email.refresh_from_db()
    assert email.subject == "Updated subject"
    assert email.body == "Test content"

    # but not when the email has been sent
    email.sent = True
    email.save()
    response = get_view_for_user(
        viewname="emails:metadata-update",
        client=client,
        method=client.post,
        data={"subject": "Updated again"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403
    email.refresh_from_db()
    assert email.subject == "Updated subject"
    assert email.body == "Test content"


@pytest.mark.django_db
def test_email_body_update(client):
    user = UserFactory()
    email = EmailFactory(subject="Test email", body="Test content")
    response = get_view_for_user(
        viewname="emails:body-update",
        client=client,
        method=client.post,
        data={"body": "Updated content"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403

    # only users with permission can create emails
    assign_perm("emails.change_email", user)
    response = get_view_for_user(
        viewname="emails:body-update",
        client=client,
        method=client.post,
        data={"body": "Updated content"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 302
    email.refresh_from_db()
    assert email.subject == "Test email"
    assert email.body == "Updated content"

    # but not when the email has been sent
    email.sent = True
    email.save()
    response = get_view_for_user(
        viewname="emails:body-update",
        client=client,
        method=client.post,
        data={"body": "New content"},
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403
    email.refresh_from_db()
    assert email.subject == "Test email"
    assert email.body == "Updated content"


@pytest.mark.django_db
def test_email_detail_permission(client):
    user = UserFactory()
    email = EmailFactory(subject="Test email", body="Test content")
    response = get_view_for_user(
        viewname="emails:detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403

    # only users with permission can view emails
    assign_perm("emails.view_email", user)
    response = get_view_for_user(
        viewname="emails:detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_email_rendered_detail_get_permission(client):
    user = UserFactory()
    email = EmailFactory(subject="Test email", body="Test content")
    response = get_view_for_user(
        viewname="emails:rendered-detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 403

    # only users with permission can view emails
    assign_perm("emails.view_email", user)
    response = get_view_for_user(
        viewname="emails:rendered-detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
    )
    assert response.status_code == 200
    assert "Dear AnonymousUser," in response.rendered_content
    assert "Test content" in response.rendered_content

    # Should use a system email without an unsubscribe link
    # as the generated email is for the anonymous user, not the request.user
    assert (
        "This is an automated service email from" in response.rendered_content
    )


@pytest.mark.django_db
def test_email_rendered_detail_get_post_permission(client):
    user = UserFactory()
    email = EmailFactory(subject="Test email", body="Test content")
    response = get_view_for_user(
        viewname="emails:rendered-detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
        method=client.post,
        data={"content": "New content"},
    )
    assert response.status_code == 403

    # only users with permission can view emails
    assign_perm("emails.view_email", user)
    response = get_view_for_user(
        viewname="emails:rendered-detail",
        client=client,
        reverse_kwargs={"pk": email.pk},
        user=user,
        method=client.post,
        data={"content": "New content"},
    )
    assert response.status_code == 200
    assert "Dear AnonymousUser," in response.rendered_content
    assert "New content" in response.rendered_content

    # The email shouldn't be updated as the post is only a preview
    email.refresh_from_db()
    assert email.body == "Test content"


@pytest.mark.django_db
def test_email_list_permission(client):
    user = UserFactory()
    email1, email2 = EmailFactory.create_batch(2)
    response = get_view_for_user(
        viewname="emails:list",
        client=client,
        user=user,
    )
    assert response.status_code == 403

    # only users with permission can create emails
    assign_perm("emails.view_email", user)
    response = get_view_for_user(
        viewname="emails:list",
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert email1.subject in response.rendered_content
    assert email2.subject in response.rendered_content
