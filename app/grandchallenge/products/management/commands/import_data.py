from django.core.management import BaseCommand

from grandchallenge.products.utils import DataImporter


class Command(BaseCommand):
    help = "Reads excel database and creates sqlite database"

    def add_arguments(self, parser):
        parser.add_argument("dir_products", type=str)
        parser.add_argument("dir_companies", type=str)

    def handle(self, *args, **options):
        data_source_p = options.pop("dir_products")
        data_source_c = options.pop("dir_companies")

        di = DataImporter()
        di.import_data(product_data=data_source_p, company_data=data_source_c)
