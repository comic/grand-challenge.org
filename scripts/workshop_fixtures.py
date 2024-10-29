import random
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from PIL import Image as PILImage

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceSuperKindChoices,
)
from grandchallenge.evaluation.models import Phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import Invoice
from grandchallenge.pages.models import Page
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import Workstation

CHALLENGE_TITLES = [
    "Alpha-Atlas",
    "Beta-Breeze",
    "Crimson-Code",
    "Delta-Drive",
    "Echo-Engine",
    "Frost-Forge",
    "Gamma-Grid",
    "Hydra-Haven",
    "Ion-Infinity",
    "Jade-Journey",
    "Kinetic-Key",
    "Lunar-Link",
    "Mystic-Matrix",
    "Nova-Nexus",
    "Omega-Orbit",
]

WORKSHOP_HOST_USERNAMES = [
    "amickan",
    "chris.vanrun.diag",
    "ammar.ammar",
    "koopman.t",
]

ALGORITHM_WORKSTATION_CONFIG_SLUG = "workshop-demo-vessel-segmentation"


def run():
    for challenge in CHALLENGE_TITLES:
        ch, archive = create_challenge(
            title=challenge,
        )
        print(
            f"Challenge: {ch.get_absolute_url()} "
            f"Archive: {archive.get_absolute_url()}"
        )


def create_challenge(*, title):
    admins = (
        get_user_model()
        .objects.filter(username__in=WORKSHOP_HOST_USERNAMES)
        .all()
    )

    c = Challenge.objects.create(
        title=title,
        short_name=title,
        creator=admins[0],
        contact_email="support@grand-challenge.org",
    )
    _upload_challenge_logo(challenge=c)

    for admin in admins[1:]:
        c.add_admin(admin)

    page = Page.objects.get(
        challenge=c,
    )
    page.content_markdown = 'This is a demo challenge for the <a href="https://workshop2024.grand-challenge.org/">Challenge Hosting Masterclass 2024</a>.'
    page.save()

    Invoice.objects.create(
        challenge=c,
        support_costs_euros=0,
        compute_costs_euros=20,
        storage_costs_euros=10,
        payment_status=Invoice.PaymentStatusChoices.COMPLIMENTARY,
    )

    phase_title = "Test"

    archive = _create_phase_archive(
        editors=admins,
        title=f"{c.short_name} {phase_title} dataset",
    )

    wk = Workstation.objects.get(slug=settings.DEFAULT_WORKSTATION_SLUG)
    wk_config = WorkstationConfig.objects.get(
        slug=ALGORITHM_WORKSTATION_CONFIG_SLUG
    )

    p = Phase.objects.create(
        challenge=c,
        title=phase_title,
        algorithm_time_limit=300,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        archive=archive,
        submissions_limit_per_user_per_period=5,
        workstation=wk,
        workstation_config=wk_config,
    )

    p.algorithm_inputs.set(_get_inputs())
    p.algorithm_outputs.set(_get_outputs())

    return c, archive


def _get_inputs():
    return ComponentInterface.objects.filter(
        slug__in=["color-fundus-image", "age-in-months"]
    )


def _get_outputs():
    return ComponentInterface.objects.filter(
        slug__in=["binary-vessel-segmentation"]
    )


def _create_phase_archive(*, editors, title):
    archive = Archive.objects.create(
        title=title,
        workstation=Workstation.objects.get(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        ),
    )
    _upload_challenge_logo(challenge=archive)
    for editor in editors:
        archive.add_editor(editor)

    _create_archive_item(archive=archive)

    return archive


def _upload_challenge_logo(*, challenge):
    path = Path(__file__).parent / "resources" / "workshop-2024" / "logo.png"
    with open(path, "rb") as f:
        file = File(f, name="logo.png")
        challenge.logo.save(file.name, file, save=True)


def _create_archive_item(*, archive):
    ai = ArchiveItem.objects.create(archive=archive)
    interfaces = _get_inputs()

    for interface in interfaces:
        if interface.super_kind == InterfaceSuperKindChoices.IMAGE:
            ai.values.add(
                _create_image_civ(
                    interface=interface, image_name="00_fundus_image.jpg"
                )
            )
        elif interface.super_kind == InterfaceSuperKindChoices.VALUE:
            ai.values.add(
                _create_value_civ(
                    interface=interface, value=random.randint(216, 999)
                )
            )


def _create_value_civ(*, interface, value):
    civ = ComponentInterfaceValue.objects.create(
        interface=interface, value=value
    )
    return civ


def _create_image_civ(*, interface, image_name):
    civ = ComponentInterfaceValue.objects.create(interface=interface)

    path = Path(__file__).parent / "resources" / "workshop-2024" / image_name

    with open(path, "rb") as f:
        pil_image = PILImage.open(f)
        width, height = pil_image.size
        im = Image.objects.create(name=image_name, width=width, height=height)
        im_file = ImageFile.objects.create(image=im)
        im_file.file.save(image_name, f)
        im_file.save()

    civ.image = im
    civ.save()

    return civ
