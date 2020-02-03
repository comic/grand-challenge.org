from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename

from grandchallenge.core.storage import public_s3_storage


def get_logo_path(instance, filename):
    return f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


def get_images_path(instance, filename):
    return f"product_images/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


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
        upload_to=get_logo_path, storage=public_s3_storage, null=True,
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
        upload_to=get_images_path, storage=public_s3_storage
    )


# Create your models here.
class ProductEntry(models.Model):
    STATUS_CERTIFIED = "cer"
    STATUS_YES = "yes"
    STATUS_NO = "no"
    STATUS_NA = "na"
    STATUS_CLEARED = "cle"
    STATUS_DE_NOVO_CLEARED = "dnc"
    STATUS_PMA_APPROVED = "pma"
    STATUS_UNKNOWN = "unk"

    VERFIFIED_CHOICES = ((STATUS_YES, "Yes"), (STATUS_NO, "No"))

    CE_STATUS_CHOICES = (
        (STATUS_CERTIFIED, "Certified"),
        (STATUS_NO, "No or not yet"),
        (STATUS_NA, "Not applicable"),
        (STATUS_UNKNOWN, "Unknown"),
    )

    FDA_STATUS_CHOICES = (
        (STATUS_CLEARED, "510(k) cleared"),
        (STATUS_DE_NOVO_CLEARED, "De novo 510(k) cleared"),
        (STATUS_PMA_APPROVED, "PMA approved"),
        (STATUS_NO, "No or not yet"),
        (STATUS_NA, "Not applicable"),
        (STATUS_UNKNOWN, "Unknown"),
    )

    ICONS = {
        STATUS_CERTIFIED: "icon_check.png",
        STATUS_YES: "icon_check.png",
        STATUS_NO: "icon_no.png",
        STATUS_NA: "icon_na.png",
        STATUS_CLEARED: "icon_check.png",
        STATUS_DE_NOVO_CLEARED: "icon_check.png",
        STATUS_PMA_APPROVED: "icon_check.png",
        STATUS_UNKNOWN: "icon_question.png",
    }

    created_date = models.DateField(default=timezone.now)
    modified_date = models.DateField(default=timezone.now)
    published_date = models.DateField(blank=True, null=True)
    product_name = models.CharField(max_length=200)
    company = models.ForeignKey(
        CompanyEntry, on_delete=models.CASCADE
    )  # product.company.company_name
    short_name = models.CharField(
        max_length=500,
        blank=False,
        help_text=(
            "short name used in url, specific css, files etc. No spaces allowed"
        ),
        unique=True,
    )
    description = models.CharField(
        max_length=400,
        default="",
        blank=True,
        help_text="Short summary of this project, max 300 characters.",
    )
    description_short = models.CharField(
        max_length=250,
        default="",
        blank=True,
        help_text="Short summary of this project, max 250 characters.",
    )
    modality = models.CharField(max_length=100)
    subspeciality = models.CharField(max_length=300)
    diseases = models.CharField(max_length=200)
    population = models.CharField(max_length=200)

    input_data = models.CharField(max_length=150)
    file_format_input = models.CharField(max_length=500)
    output_data = models.CharField(max_length=150)
    file_format_output = models.CharField(max_length=500)
    key_features = models.CharField(max_length=200)
    key_features_short = models.CharField(max_length=120)
    software_usage = models.CharField(max_length=300)

    verified = models.CharField(
        choices=VERFIFIED_CHOICES, max_length=3, default=STATUS_NO
    )
    ce_status = models.CharField(
        choices=CE_STATUS_CHOICES, max_length=3, default=STATUS_NO
    )
    ce_class = models.CharField(max_length=500, default="unknown")
    fda_status = models.CharField(
        choices=FDA_STATUS_CHOICES, max_length=3, default=STATUS_UNKNOWN
    )
    fda_class = models.CharField(max_length=500, default="unknown")
    ce_verified = models.CharField(
        choices=VERFIFIED_CHOICES, max_length=3, default=STATUS_NO
    )

    integration = models.CharField(max_length=500, default="unknown")
    deployment = models.CharField(max_length=500, default="unknown")
    process_time = models.CharField(max_length=500)
    trigger = models.CharField(max_length=100)

    market_since = models.CharField(
        max_length=500, default="unknown"
    )  # choose only month year in datefield?
    countries = models.CharField(max_length=500, default="unknown")
    distribution = models.CharField(max_length=100, default="unknown")
    institutes_research = models.CharField(max_length=500, default="unknown")
    institutes_clinic = models.CharField(max_length=500, default="unknown")

    pricing_model = models.CharField(max_length=500, default="unknown")
    pricing_basis = models.CharField(max_length=500, default="unknown")

    tech_papers = models.CharField(max_length=500, default="unknown")
    clin_papers = models.CharField(max_length=500, default="unknown")
    tech_peer_papers = models.CharField(max_length=500, default="unknown")
    tech_other_papers = models.CharField(max_length=500, default="unknown")
    all_other_papers = models.CharField(max_length=500, default="unknown")

    images = models.ManyToManyField(ProductImage)

    def __str__(self):
        return self.short_name
