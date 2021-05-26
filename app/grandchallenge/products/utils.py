import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from django.core.files.images import ImageFile
from django.utils.text import slugify


from grandchallenge.products.models import (
    Company,
    Product,
    ProductImage,
    Status,
)


STATUS_MAPPING = {
    "Certified": Status.CERTIFIED,
    "No or not yet": Status.NO,
    "Not applicable": Status.NA,
    "510(k) cleared": Status.CLEARED,
    "De novo 510(k) cleared": Status.DE_NOVO_CLEARED,
    "PMA approved": Status.PMA_APPROVED,
    "Yes": Status.YES,
    "No": Status.NO,
}

CE_MAPPING = {
    "Medical Devices Directive (MDD)": "MDD",
    "Medical Device Regulation (MDR)": "MDR",
    "Medical Devices Directive (MDD), Medical Device Regulation (MDR)": "MDD/MDR",
}


class DataImporter:
    def __init__(self):
        self.images_path = Path(".")

    def _read_data(self, data_dir):
        df = pd.read_excel(data_dir)
        df = df.fillna(value="")
        return df

    def import_data(self, *, product_data, company_data, images_zip=None):
        df_c = self._read_data(company_data)
        df_p = self._read_data(product_data)
        tmpdir = None

        # Delete all existing entries and recreate them
        Company.objects.all().delete()
        Product.objects.all().delete()
        ProductImage.objects.all().delete()

        if images_zip:
            tmpdir = tempfile.mkdtemp()
            with zipfile.ZipFile(images_zip) as zipf:
                zipf.extractall(tmpdir)
            self.images_path = Path(tmpdir)

        for _, c_row in df_c.iterrows():
            c = self._create_company(c_row)
            df_filter = df_p.loc[df_p["Company name"] == c_row["Company name"]]
            for _, p_row in df_filter.iterrows():
                product = self._create_product(p_row, c)
                self._create_product_images(product, p_row)

        if tmpdir:
            shutil.rmtree(tmpdir)

    def _split(self, string, max_char):
        if len(string) > max_char:
            short_string = string[:max_char].rsplit(" ", 1)[0] + " ..."
        else:
            return string
        return short_string

    def _create_company(self, row):
        c = Company()
        c.company_name = row["Company name"]
        c.modified = row["Timestamp"]
        c.website = row["Company website url"]
        c.founded = row["Founded"]
        c.hq = row["Head office"]
        c.email = row["Email address (public)"]
        c.description = row["Company description"]
        c.description_short = self._split(row["Company description"], 200)
        slug = slugify(row["Company name"])
        c.slug = slug
        img_file = self.images_path.glob(f"**/logo/{slug}.*")
        for file in img_file:
            c.logo = ImageFile(open(file, "rb"))
        c.save()
        return c

    def _create_product(self, row, c):
        p = Product()
        p.product_name = row["Product name"]
        p.company = c
        p.modified = row["Timestamp"]
        p.slug = slugify(row["Short name"])
        p.description = row["Product description"]
        p.description_short = self._split(row["Product description"], 200)
        p.modality = row["Modality"]
        p.subspeciality = row["Subspeciality"]
        p.input_data = row["Input data"]
        p.file_format_input = row["File format of input data"]
        p.output_data = row["Output data"]
        p.file_format_output = row["File format of output data"]
        p.key_features = row["Key-feature(s)"]
        p.ce_status = STATUS_MAPPING.get(row["CE-certified"], Status.UNKNOWN)
        p.ce_under = CE_MAPPING.get(row["CE-certified under"], "")
        p.ce_class = row["If CE-certified, what class"]
        p.fda_status = STATUS_MAPPING.get(
            row["FDA approval/clearance"], Status.UNKNOWN
        )
        p.fda_class = row["If FDA approval/clearance, what class"]
        p.verified = STATUS_MAPPING.get(row["Verified"], Status.UNKNOWN)
        p.ce_verified = STATUS_MAPPING.get(row["CE verified"], Status.UNKNOWN)
        p.integration = row["Integration"]
        p.deployment = row["Deployment"]
        p.process_time = row["Algorithm processing time per study"]
        p.trigger = row["Trigger for the analysis of data"]
        p.market_since = str(row["Product on the market since"])
        p.countries = str(row["Number of countries present"])
        p.diseases = row["Disease(s) targeted"]
        p.population = row["Population on which analysis is applied"]
        p.distribution = str(
            row["Distribution platforms/marketplaces availability"]
        )
        p.software_usage = row[
            "Suggested use of software (before, during or after study assessment)"
        ]
        p.institutes_research = str(
            row["Number of institutes using the product for research"]
        )
        p.institutes_clinic = str(
            row["Number of institutes using the product in clinical practice"]
        )
        p.pricing_model = row["Pricing model"]
        p.pricing_basis = row["Pricing model based on"]
        p.tech_peer_papers = row[
            "Name peer reviewed papers that describe the performance of the software as is commercially available."
        ]
        p.tech_other_papers = row[
            "Name other (white)papers that describe the performance of the software as is commercially available."
        ]
        p.all_other_papers = row[
            "Name other relevant (white)papers regarding the performance or implementation of the software not mentioned above."
        ]

        p.save()
        return p

    def _create_product_images(self, product, row):
        images = []
        img_files = self.images_path.glob(
            "**/product_images/{}*".format(row["Short name"])
        )
        product.images.all().delete()
        for file in img_files:
            img = ImageFile(open(file, "rb"))
            i = ProductImage(img=img)
            i.save()
            images.append(i)
        product.images.set(images)
