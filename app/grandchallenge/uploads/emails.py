from django.conf import settings

from grandchallenge.core.utils.email import send_templated_email


def send_file_uploaded_notification_email(**kwargs):
    challenge = kwargs["challenge"]
    title = f"[{challenge.short_name.lower()}] New Upload"
    admins = challenge.get_admins()
    if not admins:
        admin_email_adresses = [x[1] for x in settings.MANAGERS]
        kwargs["additional_message"] = (
            "<i> Message from grand-challenge: I could not\
        find any administrator for "
            + challenge.short_name
            + ". Somebody needs to know about this new upload, so I am Sending this "
            "email to everyone set as general grand challenge admin (MANAGERS in "
            "the settings conf file). To stop getting these messages, "
            "set an admin for" + challenge.short_name + ".</i> <br/><br/>"
        )
    else:
        kwargs["additional_message"] = ""
        admin_email_adresses = [x.email for x in admins]
    kwargs["project"] = challenge
    send_templated_email(
        title,
        "uploads/emails/file_uploaded_email.html",
        kwargs,
        admin_email_adresses,
    )
