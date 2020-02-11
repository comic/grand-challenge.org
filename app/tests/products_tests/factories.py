import factory

from grandchallenge.products.models import (
    Company,
    Product,
    ProductImage,
)


class CompanyFactory(factory.DjangoModelFactory):
    class Meta:
        model = Company

    company_name = factory.Sequence(lambda n: f"Company {n}")
    founded = 2010


class ProductFactory(factory.DjangoModelFactory):
    class Meta:
        model = Product

    product_name = factory.Sequence(lambda n: f"Product {n}")
    short_name = factory.Sequence(lambda n: f"product-{n}")
    company = factory.SubFactory(CompanyFactory)


class ProductImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductImage
