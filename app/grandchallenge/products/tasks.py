from celery import shared_task
from django.conf import settings

from grandchallenge.products.utils import DataImporter
from grandchallenge.uploads.models import UserUpload


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def import_product_data(*, product_data_pk, company_data_pk, images_zip_pk):
    di = DataImporter()
    di.import_data(
        product_data=UserUpload.objects.get(pk=product_data_pk),
        company_data=UserUpload.objects.get(pk=company_data_pk),
        images_zip=UserUpload.objects.get(pk=images_zip_pk),
    )
