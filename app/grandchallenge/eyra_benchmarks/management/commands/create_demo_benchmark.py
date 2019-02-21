# import os, django
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management import BaseCommand

from userena.models import UserenaSignup
from grandchallenge.evaluation.models import Method
from grandchallenge.eyra_benchmarks.models import Benchmark
from grandchallenge.eyra_data.models import DataFile, DataType


class Command(BaseCommand):
    def handle(self, *args, **options):
        def clean():
            User.objects.all().delete()
            Benchmark.objects.all().delete()
            DataType.objects.all().delete()
            DataFile.objects.all().delete()
            Method.objects.all().delete()

        def create_user():
            demouser = UserenaSignup.objects.create_user(
                username="admin",
                email="admin@example.com",
                password="admin",
                active=True,
            )
            demouser.is_staff = True
            demouser.save()
            return demouser

        def create_test_data_types(user):
            image_set_type = DataType(
                name='GrayScaleImageSet',
                description='Set of grayscale images (.npy)',
            )
            image_set_type.save()

            output_metrics_type = DataType(
                name='OutputMetrics',
                description='Metrics (.json)'
            )
            output_metrics_type.save()

        def create_data_files(user):
            test_images = DataFile(
                creator=user,
                name='Demo challenge test images',
                description='Demo challenge test images',
                type=DataType.objects.get(name='GrayScaleImageSet'),
                is_public=False,
            )

            test_images.save()

            test_file = File(open('/home/tom/Projects/eyra/grand-challenge.org/app/grandchallenge/eyra_benchmarks/management/commands/X_test.npy'))
            test_images.file.save('filename.png', test_file, save=True)


        def create_demo_benchmark(user: User):
            demo = Benchmark(
                name='Demo for tissue segmentation',
                description='''
            * Demo Challenge
            This benchmark is set up for illustrative purposes, with the aim to provide an example of an
            insight challenge and show that additional analyses can be done beyond the leaderboard.
                        ''',
                creator=user,
                # task_types=[TaskType.objects.get_or_create(type='Segmentation')],
            )

            demo.save()
            return demo

        clean()
        demouser = create_user()
        create_test_data_types(demouser)
        create_data_files(demouser)
        # demo = create_demo_benchmark(demouser)



        # create_data(demo)

        # demo.add_participant(demoparticipant)
        # Page.objects.create(
        #     challenge=demo, title="all", permission_lvl="ALL"
        # )
        # Page.objects.create(
        #     challenge=demo, title="reg", permission_lvl="REG"
        # )
        # Page.objects.create(
        #     challenge=demo, title="adm", permission_lvl="ADM"
        # )

        # method = Method(challenge=demo, creator=demoadmin)
        # container = ContentFile(base64.b64decode(b""))
        # method.image.save("test.tar", container)
        # method.save()
        #
        # submission = Submission(challenge=demo, creator=demoparticipant)
        # content = ContentFile(base64.b64decode(b""))
        # submission.file.save("test.csv", content)
        # submission.save()
        #
        # job = Job.objects.create(submission=submission, method=method)
        #
        # Result.objects.create(
        #     challenge=demo,
        #     metrics={
        #         "acc": {"mean": 0.5, "std": 0.1},
        #         "dice": {"mean": 0.71, "std": 0.05},
        #     },
        #     job=job,
        # )

        # demo.evaluation_config.score_title = "Accuracy ± std"
        # demo.evaluation_config.score_jsonpath = "acc.mean"
        # demo.evaluation_config.score_error_jsonpath = "acc.std"
        # demo.evaluation_config.extra_results_columns = [
        #     {
        #         "title": "Dice ± std",
        #         "path": "dice.mean",
        #         "error_path": "dice.std",
        #         "order": "desc",
        #     }
        # ]
        #
        # demo.evaluation_config.save()

        # def create_method(challenge):
        #     # todo: put in evaluation container
        #     method = Method(
        #         challenge=challenge
        #     )
        #     method.save()
        #
        # create_method(demo)

# todo: create sample algorithms
