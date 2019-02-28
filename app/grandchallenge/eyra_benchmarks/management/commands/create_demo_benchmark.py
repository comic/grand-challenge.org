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

        def create_test_data_files(user):
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

        def create_training_data_files(user):
            training_images = DataFile(
                creator=user,
                name='Demo challenge training images',
                description='Demo challenge training images',
                type=DataType.objects.get(name='GrayScaleImageSet'),
            )

            training_images.save()

            download_to_file_field(
                'https://github.com/EYRA-Benchmark/demo-algorithm-a/raw/master/preprocessed_data/X_train.npy',
                training_images.file
            )
            training_images.sha = hashlib.sha1(training_images.file.read()).hexdigest()
            training_images.original_file_name = 'X_train.npy'
            training_images.save()

            training_gt_images = DataFile(
                creator=user,
                name='Demo challenge Training ground truth images',
                description='Demo challenge Training ground truth images',
                type=DataType.objects.get(name='GrayScaleImageSet'),
            )

            training_gt_images.save()

            download_to_file_field(
                'https://github.com/EYRA-Benchmark/demo-algorithm-a/raw/master/preprocessed_data/gt_train.npy',
                training_gt_images.file)
            training_gt_images.sha = hashlib.sha1(training_gt_images.file.read()).hexdigest()
            training_gt_images.original_file_name = 'gt_train.npy'
            training_gt_images.save()

            return training_images, training_gt_images

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


        def create_demo_benchmark(user: User, evaluator: Algorithm, test_data: DataFile, gt_data: DataFile, training_data: DataFile, training_ground_truth: DataFile, interface: Interface) -> Benchmark:
            demo = Benchmark(
                name='Demo for tissue segmentation',
                description="This benchmark is set up for illustrative purposes, with the aim to provide an example of an **insight challenge** and show that additional analyses can be done **beyond the leaderboard**.\r\n\r\n\r\n### Research problem\r\n\r\nVolumentric quantification of brain tissues has shown to be valuable for the diagnosis, progression and treatment monitoring of numerous neurological conditions, such as Alzheimer's disease and multiple scleroris [1]. \r\nConsidering the large amount of existing brain tissue segmentation methods as well as available data, there is a need for systematic comparison of these algorithms. The aim of this benchmark is to compare automatic algorithms for segmentation of grey matter (GM), white matter (WM) and cerebrospinal fluid (CSF) on T1-weighted 3.0 Tesla simulated MRI scans of the brain. \r\n\r\nThe task of the benchmark is to segment grey matter, white matter and cerebrospinal fluid. \r\n\r\n\r\n#### Type of benchmark\r\n\r\nThere are two types of benchmark challenges: insight and deployment challenges [2]. The objective of a deployment challenge is to find algorithms that successfully solve a specific problem. To be able to make such generalizations, a quantitative benchmark design is needed. \r\n\r\nAn insight challenge, on the other hand, has the objective to gain an understanding of what class(es) of algorithms can be useful for a certain research problem. For such a benchmark, a qualitative design is sufficient. Insight challenges are useful for determining future research directions. Additionally, they are useful for investating which aspects within a research problem are important and should be taken into account when designing a deployment challenge. \r\n\r\nThis benchmark is an insight challenge, which entails that we adopt a qualitative design. We aim to understand what class of algorithms is effective for MRI brain tissue segmentation. This knowlegde can then be used for further research and benchmarking. The aim here is *not* to generalize the results to tissue segmentation in general and find the best algorithms for this task. The data that we use is not a representative sample of all cases and thus also not suitable to make such inferences.\r\n\r\n\r\n### Benchmark workflow\r\n\r\n1.\tDownload the 5 training data sets\r\n2.\tUse the training data to develop an algorithm\r\n3.\tSubmit your segmentation algorithm to the EYRA benchmark platform\r\n4.\tYour algorithm will be applied to 15 test data sets\r\n5.\tResults based on the metrics will be published on the public leaderboard \r\n\r\n\r\n### Data\r\n\r\n20 fully annotated single-sequence T1-weighted 3.0 Tesla MRI brain scans are available (pixel size: 1.0x1.0mm, image size: 256x256 pixels). The scans have been simulated using the SIMRI [3] simulator, where realistic brain phantoms were used as input. The phantoms have been obtained from Brainweb (http://www.bic.mni.mcgill.ca/brainweb/) [4, 5, 6, 7] and consist of transverse slices of 20 subjects with a normal, healthy brain. \r\n\r\nThe following acquisition parameters were used for the simulation of the scans: pulse sequence: T1-weighted (SE), field strength: 3.0 Tesla, TR: 520, TE: 15, flip angle: 90&deg;. These acquisition parameters were based on optimal scan parameters for 3.0 Tesla scanners [8].\r\n\r\n\r\n#### Types of variation\r\n\r\nMedrik and Aylward [3] give an overview of aspects that can be varied.\r\n\r\n--> Adrienne overleggen\r\n\r\n\r\n### Training, testing and holdout data\r\n\r\n5 data sets (scans), with manual segmentations, are provided to use as training data. 15 data sets are used for testing the algorithm. Participants do not have access to the test data sets. Once an algorithm is submitted to the EYRA benchmark platform, it will be applied to the 15 test data sets. For this benchmark there is no additional holdout data.\r\n\r\n\r\n### Reference standard/ground truth\r\n\r\nThe manual segmentations were obtained from Brainweb. The manual segmentations denote the tissue class with the largest proportion in each pixel.\r\n\r\n\r\n### Algorithm evaluation\r\n\r\nSubmitted segmentation algorithms will be applied to the test data. Predicted tissue classes will be obtained and compared to the manual segmentations. The following metrics are used as algorithm evaluation: the Dice coefficient (DC) and the absolute volume difference (AVD). \r\n\r\n\r\n#### Dice coefficient\r\n\r\n\r\nThe DC is a measure of spatial overlap, expressed as a percentage:\r\n\r\n$$ D = \\frac{2 \\left| A \\cap G \\right|}{\\left| A \\right| + \\left| G \\right|} * 100, $$\r\n\r\nwhere $A$ is the segmentation result and $G$ the ground truth.\r\n\r\n\r\n#### Absolute volume difference\r\n\r\n\r\nThe AVD is the percentage absolute volume difference:\r\n\r\n$$ AVD = \\frac{\\left| V_a - V_g \\right|}{V_g} * 100, $$\r\n\r\nwhere $V_a$ is the volume of the segmentation result. $V_g$ is the volume of the ground truth.\r\n\r\n<br>\r\n\r\n1. The DC and AVD will be calculated for each data set and each tissue type (GM, WM, CSF) \r\n2. The final ranking of the leaderboard is based on the results of all 15 test datasets\r\n    - Mean value over all 15 data set is determined for GM, WM and CSF. \r\n    - Each partipant receives a rank for each tissue type (GM, WM, CSF) and each evaluation metric (DC, AVD)\r\n    - Final score is determined by adding the ranks for each time (rank of all tissue types and evaluation measures)\r\n    \r\n--> Adrienne overleggen  \r\n--> Paper Lena ergens vermelden?\r\n    \r\n    \r\nAutomatic evaluation is used, metric software is automatically applied to compare the ground truth and algorithm segmentation results.",
                short_description="This benchmark is set up for illustrative purposes, with the aim to provide an example of an **insight challenge** and show that additional analyses can be done **beyond the leaderboard**.",
                creator=user,
                evaluator=evaluator,
                test_data_file=test_data,
                test_ground_truth_data_file=gt_data,
                training_data_file=training_data,
                training_ground_truth_data_file=training_ground_truth,
                interface=interface,
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
        training_data, training_gt_data = create_training_data_files(demouser)
        test_data, test_gt_data = create_test_data_files(demouser)
        eval_interface = create_eval_interface()
        evaluator = create_evaluator(demouser, eval_interface)
        predictor_interface = create_predict_interface()
        demo_benchmark = create_demo_benchmark(demouser, evaluator, test_data, test_gt_data, training_data, test_gt_data, predictor_interface)
        predictor_a = create_predictor(demouser, predictor_interface)
        submission_a = create_submission(demouser, demo_benchmark, predictor_a)
