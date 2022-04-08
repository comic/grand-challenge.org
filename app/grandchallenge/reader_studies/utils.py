import logging

from django.db import transaction

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.reader_studies.models import Answer, DisplaySet
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)


def _get_civ(image, slug):
    try:
        ci = ComponentInterface.objects.get(slug=slug)
    except ComponentInterfaceValue.DoesNotExist:
        raise ValueError(f"ComponentInterface {slug} does not exist.")

    civ, _ = ComponentInterfaceValue.objects.get_or_create(
        image=image, interface=ci
    )
    return civ


def migrate_reader_study_to_display_sets(rs, view_content):  # noqa: C901
    if not rs.is_valid:
        raise ValueError("Reader study is not valid")

    with transaction.atomic():
        for item in rs.hanging_list:
            ds = DisplaySet.objects.create(reader_study=rs)
            images = []
            for key in item:
                if "overlay" in key:
                    continue
                try:
                    slugs = view_content[key]
                except KeyError:
                    raise ValueError(
                        f"No ComponentInterface provided for {key}."
                    )
                if len(slugs) == 0:
                    raise ValueError(
                        f"No ComponentInterface provided for {key}."
                    )
                else:
                    if len(slugs) > 2:
                        logger.warning(
                            f"More than two interface slugs provided for {key} "
                            f"in {rs.slug}. Ignoring all values after the second."
                        )
                    image = rs.images.get(name=item[key])
                    ds.values.add(_get_civ(image, slugs[0]))
                    images.append(image.pk)

                    overlay = item.get(f"{key}-overlay")
                    if overlay is None:
                        continue
                    overlay = rs.images.get(name=overlay)
                    ds.values.add(_get_civ(overlay, slugs[1]))
                    images.append(overlay.pk)

            answers = Answer.objects.filter(
                question__reader_study=rs
            ).prefetch_related("images")

            for image in images:
                answers = answers.filter(images=image)

            for answer in answers:
                try:
                    _assign_answer_to_display_set(
                        answer=answer, display_set=ds
                    )
                except Exception:
                    # Answer does not belong to this display set
                    continue

        rs.use_display_sets = True
        rs.hanging_list = []
        if rs.workstation.slug == "cirrus-core-previous-release":
            new_ws = Workstation.objects.get(slug="cirrus-core")
            rs.workstation = new_ws
        rs.save()


def _assign_answer_to_display_set(answer, display_set):
    if {
        v.image.pk for v in display_set.values.select_related("image").all()
    } != {im.pk for im in answer.images.all()}:
        raise RuntimeError("Answer and displayset do not match")

    answer.display_set = display_set
    answer.save()
    answer.images.clear()


def check_for_new_answers(rs):
    # Check of any new answers have been created during the migration
    # and add them to the proper display set
    errors = []

    with transaction.atomic():
        for answer in Answer.objects.filter(
            question__reader_study=rs, images__isnull=False
        ):
            ds = DisplaySet.objects.filter(reader_study=rs)

            for im in answer.images.all():
                ds = ds.filter(values__image=im)

            try:
                ds = ds.get()
                _assign_answer_to_display_set(answer=answer, display_set=ds)
            except Exception:
                errors.append(str(answer.pk))

    if errors:
        raise ValueError(
            f"Could not find a display set for answers {', '.join(errors)}."
        )
