from django.db import models
from django.utils import timezone


class CompanyEntry(models.Model):
    # author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_date = models.DateField(default=timezone.now)
    modified_date = models.DateField(auto_now=True)
    published_date = models.DateField(blank=True, null=True)
    company_name = models.CharField(max_length=200)
    website = models.URLField(max_length=50)
    founded = models.IntegerField()
    hq = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    # logo = models.ImageField(upload_to=get_logo_path, blank=True)
    description = models.CharField(
        max_length=500,
        default="",
        blank=True,
        help_text="Short summary of this project, max 500 characters.",
    )

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.company_name


class ProductBasic(models.Model):
    # author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_date = models.DateField(default=timezone.now)
    modified_date = models.DateField(auto_now=True)
    product_name = models.CharField(max_length=200)
    # company_name = models.CharField(max_length=200)
    company = models.ForeignKey(
        CompanyEntry, on_delete=models.CASCADE
    )  # product.company.company_name
    short_name = models.CharField(
        max_length=50,
        blank=False,
        help_text=(
            "short name used in url, specific css, files etc. No spaces allowed"
        ),
        unique=True,
    )
    description = models.CharField(
        max_length=250,
        default="",
        blank=True,
        help_text="Short summary of this project, max 250 characters.",
    )
    modality = models.CharField(max_length=10)
    subspeciality = models.CharField(max_length=30)

    input_data = models.CharField(max_length=150)
    file_format_input = models.CharField(max_length=50)
    output_data = models.CharField(max_length=150)
    file_format_output = models.CharField(max_length=50)
    key_features = models.CharField(max_length=150)

    def __str__(self):
        return self.short_name


# Create your models here.
class ProductEntry(ProductBasic):
    ce_status = models.CharField(max_length=50, default="unknown")
    ce_class = models.CharField(max_length=50, default="unknown")
    fda_status = models.CharField(max_length=50, default="unknown")
    fda_class = models.CharField(max_length=50, default="unknown")

    integration = models.CharField(max_length=50, default="unknown")
    hosting = models.CharField(max_length=50, default="unknown")
    hardware = models.CharField(max_length=150, default=" ")

    market_since = models.CharField(
        max_length=50, default="unknown"
    )  # choose only month year in datefield?
    countries = models.CharField(max_length=50, default="unknown")
    distribution = models.CharField(
        max_length=100, default="unknown"
    )  # or list?
    institutes_research = models.CharField(max_length=50, default="unknown")
    institutes_clinic = models.CharField(max_length=50, default="unknown")

    pricing_model = models.CharField(max_length=50, default="unknown")
    pricing_basis = models.CharField(max_length=50, default="unknown")

    tech_papers = models.CharField(max_length=500, default="unknown")
    clin_papers = models.CharField(max_length=500, default="unknown")

    def __str__(self):
        return self.short_name
