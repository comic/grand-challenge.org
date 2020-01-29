import factory

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductEntry,
    ProductImage,
)


class CompanyEntryFactory(factory.DjangoModelFactory):
    class Meta:
        model = CompanyEntry

    company_name = factory.Sequence(lambda n: f"Company {n}")
    founded = 2010


class ProductEntryFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductEntry

    product_name = factory.Sequence(lambda n: f"Product {n}")
    short_name = factory.Sequence(lambda n: f"product-{n}")
    company = factory.SubFactory(CompanyEntryFactory)


class ProductImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductImage
