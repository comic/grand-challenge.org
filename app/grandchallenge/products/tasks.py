import tempfile
from pathlib import Path

from celery import shared_task
from django.conf import settings

from grandchallenge.components.backends.utils import safe_extract
from grandchallenge.products.utils import import_data
from grandchallenge.uploads.models import UserUpload


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def import_product_data(*, product_data_pk, company_data_pk, images_zip_pk):
    product_data = UserUpload.objects.get(pk=product_data_pk)
    company_data = UserUpload.objects.get(pk=company_data_pk)
    images_zip = UserUpload.objects.get(pk=images_zip_pk)

    try:
        with tempfile.TemporaryDirectory() as input_dir:
            input_dir = Path(input_dir)

            products_path = input_dir / "product_data.xlsx"
            companies_path = input_dir / "company_data.xlsx"
            images_path = input_dir / "images.zip"

            with open(products_path, "wb") as f:
                product_data.download_fileobj(f)

            with open(companies_path, "wb") as f:
                company_data.download_fileobj(f)

            with open(images_path, "wb") as f:
                images_zip.download_fileobj(f)

            extracted_images = input_dir / "images"
            extracted_images.mkdir()

            safe_extract(src=images_path, dest=extracted_images)

            import_data(
                products_path=products_path,
                companies_path=companies_path,
                images_path=extracted_images,
            )

    finally:
        # Remove the file uploads
        product_data.delete()
        company_data.delete()
        images_zip.delete()
