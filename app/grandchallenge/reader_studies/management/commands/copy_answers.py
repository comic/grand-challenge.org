from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.reader_studies.models import Answer, ReaderStudy


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("reader_study_slug", type=str)
        parser.add_argument("src_username", type=str)
        parser.add_argument("--dest-user", type=str, required=False)

    def handle(self, *args, **options):
        src_user = get_user_model().objects.get(
            username=options["src_username"]
        )
        reader_study = ReaderStudy.objects.get(
            slug=options["reader_study_slug"]
        )

        dest_users = [
            *reader_study.editors_group.user_set.exclude(pk=src_user.pk),
            *reader_study.readers_group.user_set.exclude(pk=src_user.pk),
        ]

        if options["dest_user"] is not None:
            dest_users = [
                u for u in dest_users if u.username == options["dest_user"]
            ]

        if not dest_users:
            raise ValueError("No users to copy to")

        existing_user_answers = Answer.objects.filter(
            question__reader_study=reader_study, creator__in=dest_users
        )

        if existing_user_answers.exists():
            raise RuntimeError(
                "These users have created answers for this study"
            )

        creators_answers = Answer.objects.filter(
            question__reader_study=reader_study, creator=src_user
        )

        if not creators_answers.exists():
            raise ValueError("No answers to copy")

        if creators_answers.filter(answer_image__isnull=False).exists():
            raise ValueError("Cannot copy answers with answer images")

        if creators_answers.filter(is_ground_truth=True).exists():
            raise ValueError("Cannot copy ground truth answers")

        self.stdout.write(
            f"Copy {creators_answers.count()} answers for "
            f"{reader_study.title} from {src_user.username} to "
            f"{oxford_comma(u.username for u in dest_users)}."
        )
        go = input("To continue enter 'yes': ")

        if go == "yes":
            for dest_user in dest_users:
                for src_answer in creators_answers:
                    answer = Answer.objects.create(
                        creator=dest_user,
                        question=src_answer.question,
                        answer=src_answer.answer,
                    )
                    answer.images.set(src_answer.images.all())
        else:
            raise RuntimeError(
                f"Aborting, only 'yes' is accepted, '{go}' was input"
            )
