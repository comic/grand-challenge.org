from django.db import models

from grandchallenge.challenges.models import get_logo_path


class Company(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    company_name = models.CharField(max_length=200)
    website = models.URLField()
    founded = models.IntegerField()
    hq = models.CharField(max_length=100)
    email = models.EmailField()
    logo = models.ImageField(upload_to=get_logo_path, null=True,)
    description = models.TextField(
        blank=True, help_text="Short summary of this project.",
    )
    description_short = models.CharField(
        max_length=250,
        blank=True,
        help_text="Short summary of this project, max 250 characters.",
    )

    def __str__(self):
        return self.company_name


class ProductImage(models.Model):
    img = models.ImageField(upload_to=get_logo_path)


class Product(models.Model):
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

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    product_name = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    short_name = models.CharField(
        max_length=500,
        blank=False,
        help_text=(
            "short name used in url, specific css, files etc. No spaces allowed"
        ),
        unique=True,
    )
    description = models.TextField(
        blank=True, help_text="Short summary of this project.",
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
    file_format_input = models.TextField()
    output_data = models.CharField(max_length=150)
    file_format_output = models.TextField()
    key_features = models.CharField(max_length=200)
    key_features_short = models.CharField(max_length=120)
    software_usage = models.TextField()

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

    integration = models.TextField()
    deployment = models.TextField()
    process_time = models.TextField()
    trigger = models.CharField(max_length=100)

    market_since = models.TextField()
    countries = models.TextField()
    distribution = models.CharField(max_length=100, blank=True)
    institutes_research = models.TextField()
    institutes_clinic = models.TextField()

    pricing_model = models.TextField()
    pricing_basis = models.TextField()

    tech_papers = models.TextField()
    clin_papers = models.TextField()
    tech_peer_papers = models.TextField()
    tech_other_papers = models.TextField()
    all_other_papers = models.TextField()

    images = models.ManyToManyField(ProductImage)

    def __str__(self):
        return self.short_name
