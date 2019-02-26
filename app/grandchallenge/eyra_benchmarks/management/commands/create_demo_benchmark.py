from django.core.management import BaseCommand
from django.db.models.fields.files import FieldFile
import hashlib
from django.core.files import File
from os.path import basename
from urllib.request import urlretrieve, urlcleanup
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from grandchallenge.evaluation.models import Method
from grandchallenge.eyra_algorithms.models import Input, Algorithm, Interface
from grandchallenge.eyra_benchmarks.models import Benchmark, Submission
from grandchallenge.eyra_data.models import DataFile, DataType

from userena.models import UserenaSignup


def download_to_file_field(url, field: FieldFile):
    try:
        tempname, _ = urlretrieve(url)
        field.save(basename(urlsplit(url).path), File(open(tempname, 'rb')))
    finally:
        urlcleanup()


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
            demouser.is_superuser = True
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
            )

            test_images.save()

            download_to_file_field(
                'https://github.com/EYRA-Benchmark/demo-algorithm-a/raw/master/preprocessed_data/X_test.npy',
                test_images.file
            )
            test_images.sha = hashlib.sha1(test_images.file.read()).hexdigest()
            test_images.original_file_name = 'X_test.npy'
            test_images.save()

            gt_images = DataFile(
                creator=user,
                name='Demo challenge ground truth images',
                description='Demo challenge ground truth images',
                type=DataType.objects.get(name='GrayScaleImageSet'),
            )

            gt_images.save()

            download_to_file_field(
                'https://github.com/EYRA-Benchmark/demo-algorithm-a/raw/master/preprocessed_data/gt_test.npy',
                gt_images.file)
            gt_images.sha = hashlib.sha1(gt_images.file.read()).hexdigest()
            gt_images.original_file_name = 'gt_test.npy'
            gt_images.save()

            return test_images, gt_images

        def create_eval_interface() -> Interface:
            interface = Interface(
                name='Segmentation evaluation interface',
                output_type = DataType.objects.get(name='OutputMetrics'),
            )
            interface.save()

            predictions_input = Input(
                name='predictions',
                type=DataType.objects.get(name='GrayScaleImageSet'),
                interface=interface
            )
            predictions_input.save()

            ground_truth_input = Input(
                name='ground_truth',
                type=DataType.objects.get(name='GrayScaleImageSet'),
                interface=interface
            )
            ground_truth_input.save()

            return interface

        def create_predict_interface() -> Interface:
            interface = Interface(
                name='Segmentation predictor interface',
                output_type = DataType.objects.get(name='GrayScaleImageSet'),
            )
            interface.save()

            test_input = Input(
                name='test_data',
                type=DataType.objects.get(name='GrayScaleImageSet'),
                interface=interface
            )
            test_input.save()
            return interface

        def create_evaluator(user: User, interface: Interface) -> Algorithm:
            algo = Algorithm(
                creator=user,
                name='Segmentation evaluation',
                description='Segmentation evaluation',
                container='segmentation_a_dummy',
                interface=interface
            )
            algo.save()
            return algo


        def create_demo_benchmark(user: User, evaluator: Algorithm, test_data: DataFile, gt_data: DataFile) -> Benchmark:
            demo = Benchmark(
                name='Demo for tissue segmentation',
                description='''
            * Demo Challenge
            This benchmark is set up for illustrative purposes, with the aim to provide an example of an
            insight challenge and show that additional analyses can be done beyond the leaderboard.
                        ''',
                creator=user,
                evaluator=evaluator,
                test_data_file=test_data,
                test_ground_truth_data_file=gt_data
            )
            demo.save()
            return demo

        def create_predictor(user: User, interface: Interface) -> Algorithm:
            algo = Algorithm(
                creator=user,
                name='Algorithm A',
                description='Algorithm A is the best algorithm. Even though it takes 24 hours to train',
                container='algorithm_a_0148a9ce-34f6-11e9-b346-00155d544bd9',
                interface=interface
            )
            algo.save()

            return algo

        def create_submission(user: User, benchmark: Benchmark, predictor: Algorithm) -> Submission:
            submission = Submission(
                creator=user,
                name='Algo A for tissue demo',
                benchmark=benchmark,
                algorithm=predictor,
            )
            submission.save()
            return submission


        clean()
        demouser = create_user()
        create_test_data_types(demouser)
        test_data, gt_data = create_data_files(demouser)
        eval_interface = create_eval_interface()
        evaluator = create_evaluator(demouser, eval_interface)
        demo_benchmark = create_demo_benchmark(demouser, evaluator, test_data, gt_data)
        predictor_interface = create_predict_interface()
        predictor_a = create_predictor(demouser, predictor_interface)
        submission_a = create_submission(demouser, demo_benchmark, predictor_a)
