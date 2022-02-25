import factory

from grandchallenge.products.models import Company, Product, ProductImage


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    company_name = factory.Sequence(lambda n: f"Company {n}")
    slug = factory.Sequence(lambda n: f"product-{n}")
    founded = 2010


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    product_name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.Sequence(lambda n: f"product-{n}")
    company = factory.SubFactory(CompanyFactory)


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage
