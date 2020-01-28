from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename

from grandchallenge.core.storage import public_s3_storage


def get_logo_path(instance, filename):
    return f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


class CompanyEntry(models.Model):
    # author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_date = models.DateField(default=timezone.now)
    modified_date = models.DateField(auto_now=True)
    company_name = models.CharField(max_length=200)
    website = models.URLField(max_length=500)
    founded = models.IntegerField()
    hq = models.CharField(max_length=100)
    email = models.EmailField(max_length=500)
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage, blank=True, null=True
    )
    description = models.CharField(
        max_length=500,
        default="",
        blank=True,
        help_text="Short summary of this project, max 500 characters.",
    )
    description_short = models.CharField(
        max_length=250,
        blank=True,
        help_text="Short summary of this project, max 250 characters.",
    )

    def __str__(self):
        return self.company_name


class ProductImage(models.Model):
    img = models.ImageField(
        upload_to="media/product_images/", blank=True, default=""
    )


class ProductBasic(models.Model):
    created_date = models.DateField(default=timezone.now)
    modified_date = models.DateField(auto_now=True)
    product_name = models.CharField(max_length=200)
    company = models.ForeignKey(CompanyEntry, on_delete=models.CASCADE)
    short_name = models.CharField(
        max_length=500,
        blank=False,
        help_text=(
            "short name used in url, specific css, files etc. No spaces allowed"
        ),
        unique=True,
    )
    description = models.CharField(
        max_length=300,
        default="",
        blank=True,
        help_text="Short summary of this project, max 300 characters.",
    )
    description_short = models.CharField(
        max_length=250,
        blank=True,
        help_text="Short summary of this project, max 250 characters.",
    )
    modality = models.CharField(max_length=64)
    subspeciality = models.CharField(max_length=300)

    input_data = models.CharField(max_length=150)
    file_format_input = models.CharField(max_length=500)
    output_data = models.CharField(max_length=150)
    file_format_output = models.CharField(max_length=500)
    key_features = models.CharField(max_length=150)

    def __str__(self):
        return self.short_name


# Create your models here.
class ProductEntry(ProductBasic):
    verified = models.CharField(max_length=5, default='no')
    ce_status = models.CharField(max_length=500, default="no")
    ce_class = models.CharField(max_length=500, default="unknown")
    fda_status = models.CharField(max_length=500, default="unknown")
    fda_class = models.CharField(max_length=500, default="unknown")

    integration = models.CharField(max_length=500, default="unknown")
    hosting = models.CharField(max_length=500, default="unknown")
    hardware = models.CharField(max_length=150, default=" ")

    market_since = models.CharField(
        max_length=500, default="unknown"
    )  # choose only month year in datefield?
    countries = models.CharField(max_length=500, default="unknown")
    distribution = models.CharField(
        max_length=100, default="unknown"
    )  # or list?
    institutes_research = models.CharField(max_length=500, default="unknown")
    institutes_clinic = models.CharField(max_length=500, default="unknown")

    pricing_model = models.CharField(max_length=500, default="unknown")
    pricing_basis = models.CharField(max_length=500, default="unknown")

    tech_papers = models.CharField(max_length=500, default="unknown")
    clin_papers = models.CharField(max_length=500, default="unknown")
    images = models.ManyToManyField(ProductImage)

    def __str__(self):
        return self.short_name
