from django.core.management import BaseCommand
from django.db import transaction

from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    ReaderStudy,
)


class Command(BaseCommand):
    def handle(self, *args, **options):  # noqa: C901
        not_migrated = []
        for rs in ReaderStudy.objects.filter(use_display_sets=False):
            if not (
                {x for item in rs.hanging_list for x in item}
                in [{"main"}, {"main", "main-overlay"}]
            ):
                # Multiple viewports require more interfaces, this needs
                # to be handled manually
                not_migrated.append(str(rs.pk))
                continue
            with transaction.atomic():
                image_interface = ComponentInterface.objects.get(
                    slug="generic-medical-image"
                )
                overlay_interface = ComponentInterface.objects.get(
                    slug="generic-overlay"
                )
                for item in rs.hanging_list:
                    ds = DisplaySet.objects.create(reader_study=rs)
                    images = []
                    for key in item:
                        try:
                            image = Image.objects.get(name=item[key])
                        except Image.DoesNotExist:
                            continue
                        images.append(image.pk)
                        if key == "main":
                            (
                                civ,
                                _,
                            ) = ComponentInterfaceValue.objects.get_or_create(
                                image=image, interface=image_interface
                            )
                        else:
                            (
                                civ,
                                _,
                            ) = ComponentInterfaceValue.objects.get_or_create(
                                image=image, interface=overlay_interface
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
                rs.save()

            # Check of any new answers have been created during the migration
            # and add them to the proper display set
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
                    self.stdout.write(
                        f"Could not find a display set for answer {answer.pk}."
                    )

        pk_str = "\n".join(not_migrated)
        self.stdout.write(
            f"{len(not_migrated)} reader studies could not be migrated:\n\n"
            f"{pk_str}"
        )
