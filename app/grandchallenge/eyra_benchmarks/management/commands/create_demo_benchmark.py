# import os, django
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()

from django.contrib.auth.models import User, Group
from django.core.management import BaseCommand

from userena.models import UserenaSignup
from grandchallenge.evaluation.models import Method
from grandchallenge.eyra_benchmarks.models import Benchmark
from grandchallenge.eyra_datasets.models import DataSet, DataSetType, DataSetTypeFile


class Command(BaseCommand):
    def handle(self, *args, **options):

        User.objects.all().delete()
        # Group.objects.all().delete()
        Benchmark.objects.all().delete()
        DataSetType.objects.all().delete()
        DataSetTypeFile.objects.all().delete()
        DataSet.objects.all().delete()
        Method.objects.all().delete()
        # DataSet.challenges.through.objects.all().delete()

        demoadmin = UserenaSignup.objects.create_user(
            username="demo",
            email="demo@example.com",
            password="demo",
            active=True,
        )
        UserenaSignup.objects.create_user(
            username="user",
            email="user@example.com",
            password="user",
            active=True,
        )
        adminuser = UserenaSignup.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin",
            active=True,
        )
        adminuser.is_staff = True
        adminuser.save()

        demo = Benchmark(
            title = 'Demo for tissue segmentation',
            description='''
        This benchmark is set up for illustrative purposes, with the aim to provide an example of an insight challenge and show that additional analyses can be done beyond the leaderboard.    
            ''',
            creator=demoadmin,
            # task_types=[TaskType.objects.get_or_create(type='Segmentation')],
        )

        demo.save()


        def create_data_sets(benchmark):
            combined_dataset_type, create = DataSetType.objects.get_or_create(
                name='Ground truth + data'
            )
            combined_dataset_type.save()
            type_file_data = DataSetTypeFile(
                dataset_type = combined_dataset_type,
                name='Data',
                required=True
            )
            type_file_data.save()
            type_file_ground_truth = DataSetTypeFile(
                dataset_type=combined_dataset_type,
                name='Ground truth',
                required=True
            )
            type_file_ground_truth.save()

            training_set, created = DataSet.objects.get_or_create(
                name='Training set',
                type=combined_dataset_type,
                creator=adminuser,
            )
            training_set.save()

            training_set.benchmarks.add(benchmark)

            test_set, created = DataSet.objects.get_or_create(
                name='Test set',
                type=combined_dataset_type,
                creator=adminuser,
            )

            test_set.save()
            test_set.benchmarks.add(benchmark)

        create_data_sets(demo)

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
