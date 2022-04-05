from django.db import transaction

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.reader_studies.models import Answer, DisplaySet
from grandchallenge.workstations.models import Workstation


def migrate_reader_study_to_display_sets(rs, view_content):  # noqa: C901
    with transaction.atomic():
        for item in rs.hanging_list:
            ds = DisplaySet.objects.create(reader_study=rs)
            images = []
            for key in item:
                image = rs.images.filter(name=item[key]).first()
                if image is None:
                    continue
                images.append(image.pk)
                try:
                    slug = view_content[key]
                except KeyError:
                    raise ValueError(
                        f"No ComponentInterface provided for {key}."
                    )
                try:
                    ci = ComponentInterface.objects.get(slug=slug)
                except ComponentInterfaceValue.DoesNotExist:
                    raise ValueError(
                        f"ComponentInterface {slug} does not exist."
                    )
                civ, _ = ComponentInterfaceValue.objects.get_or_create(
                    image=image, interface=ci
                )
                ds.values.add(civ)

            answers = Answer.objects.filter(question__reader_study=rs)
            for image in images:
                answers = answers.filter(images=image)
            for answer in answers:
                answer.display_set = ds
                answer.save()
                answer.images.clear()
        rs.use_display_sets = True
        rs.images.clear()
        rs.hanging_list = []
        if rs.workstation.slug == "cirrus-core-previous-release":
            new_ws = Workstation.objects.get(slug="cirrus-core")
            rs.workstation = new_ws
        rs.save()


def check_for_new_answers(rs):
    # Check of any new answers have been created during the migration
    # and add them to the proper display set
    errors = []
    for answer in Answer.objects.filter(
        question__reader_study=rs, images__isnull=False
    ):
        ds = DisplaySet.objects.filter(reader_study=rs)
        for im in answer.images.all():
            ds.filter(values__image=im)
        ds = ds.first()
        if ds:
            answer.display_set = ds
            answer.save()
            answer.images.clear()
        else:
            errors.append(str(answer.pk))

    if errors:
        raise ValueError(
            f"Could not find a display set for answers {', '.join(errors)}."
        )
