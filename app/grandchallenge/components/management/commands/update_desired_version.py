from django.core.management import BaseCommand

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.evaluation.models import Method, Phase
from grandchallenge.workstations.models import Workstation, WorkstationImage


class Command(BaseCommand):
    def handle(self, *args, **options):
        alg_images = [
            obj.latest_executable_image
            for obj in Algorithm.objects.all()
            if obj.latest_executable_image
        ]
        method_images = [
            obj.latest_executable_image
            for obj in Phase.objects.all()
            if obj.latest_executable_image
        ]
        ws_images = [
            obj.latest_executable_image
            for obj in Workstation.objects.all()
            if obj.latest_executable_image
        ]
        for image in alg_images + method_images + ws_images:
            image.is_desired_version = True
        AlgorithmImage.objects.bulk_update(alg_images, ["is_desired_version"])
        Method.objects.bulk_update(method_images, ["is_desired_version"])
        WorkstationImage.objects.bulk_update(ws_images, ["is_desired_version"])
