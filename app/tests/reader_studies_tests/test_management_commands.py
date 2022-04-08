import pytest
from django.core.management import call_command

from grandchallenge.reader_studies.models import Answer
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_migrate_to_display_sets():
    reader = UserFactory()

    rs_only_main = ReaderStudyFactory(use_display_sets=False)
    q = QuestionFactory(reader_study=rs_only_main)
    rs_only_main.add_reader(reader)
    rs_only_main_images = [ImageFactory() for _ in range(6)]
    for im in rs_only_main_images:
        rs_only_main.images.add(im)
        a = AnswerFactory(question=q, creator=reader)
        a.images.add(im)
    rs_only_main.generate_hanging_list()

    rs_main_overlay = ReaderStudyFactory(use_display_sets=False)
    rs_main_overlay.add_reader(reader)
    rs_main_overlay_images = [ImageFactory() for _ in range(6)]
    rs_main_overlay.images.set(rs_main_overlay_images)
    q = QuestionFactory(reader_study=rs_main_overlay)
    hanging_list = []
    for idx, im in enumerate(rs_main_overlay_images[:3]):
        overlay = rs_main_overlay_images[idx + 3]
        hanging_list.append(
            {
                "main": im.name,
                "main-overlay": overlay.name,
            }
        )
        a = AnswerFactory(question=q, creator=reader)
        a.images.set([im, overlay])

    rs_main_overlay.hanging_list = hanging_list
    rs_main_overlay.save()

    rs_main_secondary = ReaderStudyFactory(use_display_sets=False)
    rs_main_secondary.add_reader(reader)
    rs_main_secondary_images = [ImageFactory() for _ in range(6)]
    rs_main_secondary.images.set(rs_main_secondary_images)
    q = QuestionFactory(reader_study=rs_main_secondary)
    hanging_list = []
    for idx, im in enumerate(rs_main_secondary_images[:3]):
        secondary = rs_main_secondary_images[idx + 3]
        hanging_list.append(
            {
                "main": im.name,
                "secondary": secondary.name,
            }
        )
        a = AnswerFactory(question=q, creator=reader)
        a.images.set([im, secondary])

    rs_main_secondary.hanging_list = hanging_list
    rs_main_secondary.save()

    call_command("migrate_to_display_sets")

    rs_only_main.refresh_from_db()
    assert rs_only_main.use_display_sets is True
    # assert rs_only_main.images.count() == 0
    assert rs_only_main.display_sets.count() == 6
    assert all(
        [
            pk
            in rs_only_main.display_sets.values_list(
                "values__image_id", flat=True
            )
            for pk in [x.pk for x in rs_only_main_images]
        ]
    )
    assert (
        Answer.objects.filter(display_set__reader_study=rs_only_main).count()
        == 6
    )

    rs_main_overlay.refresh_from_db()
    assert rs_main_overlay.use_display_sets is True
    # assert rs_main_overlay.images.count() == 0
    assert rs_main_overlay.display_sets.count() == 3
    assert all(
        [
            pk
            in rs_main_overlay.display_sets.values_list(
                "values__image_id", flat=True
            )
            for pk in [x.pk for x in rs_main_overlay_images]
        ]
    )
    assert (
        Answer.objects.filter(
            display_set__reader_study=rs_main_overlay
        ).count()
        == 3
    )

    rs_main_secondary.refresh_from_db()
    assert rs_main_secondary.use_display_sets is False
    assert rs_main_secondary.images.count() == 6
    assert rs_main_secondary.display_sets.count() == 0
    assert (
        Answer.objects.filter(
            display_set__reader_study=rs_main_secondary
        ).count()
        == 0
    )
    assert (
        Answer.objects.filter(
            images__in=[x.pk for x in rs_main_secondary_images]
        )
        .distinct()
        .count()
        == 3
    )
