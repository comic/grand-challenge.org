import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from django.core.files.images import ImageFile

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductEntry,
    ProductImage,
)


STATUS_MAPPING = {
    "Certified": ProductEntry.STATUS_CERTIFIED,
    "No or not yet": ProductEntry.STATUS_NO,
    "Not applicable": ProductEntry.STATUS_NA,
    "510(k) cleared": ProductEntry.STATUS_CLEARED,
    "de novo 510(k) cleared": ProductEntry.STATUS_DE_NOVO_CLEARED,
    "PMA approved": ProductEntry.STATUS_PMA_APPROVED,
    "Yes": ProductEntry.STATUS_YES,
    "No": ProductEntry.STATUS_NO,
}


class DataImporter(object):
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
        if images_zip:
            tmpdir = tempfile.mkdtemp()
            with zipfile.ZipFile(images_zip) as zipf:
                zipf.extractall(tmpdir)
            self.images_path = Path(tmpdir)

        for i, c_row in df_c.iterrows():
            c = self._create_company(c_row)
            df_filter = df_p.loc[df_p["Company name"] == c_row["Company name"]]
            for _, p_row in df_filter.iterrows():
                i = self._create_product_images(p_row)
                self._create_product(p_row, c, i)

        if tmpdir:
            shutil.rmtree(tmpdir)

    def _split(self, string, max_char):
        if len(string) > max_char:
            short_string = string[:max_char].rsplit(" ", 1)[0] + " ..."
        else:
            return string
        return short_string

    def _create_company(self, row):
        c = CompanyEntry(
            company_name=row["Company name"],
            modified_date=row["Timestamp"],
            website=row["Company website url"],
            founded=row["Founded"],
            hq=row["Head office"],
            email=row["Email address (public)"],
            description=row["Company description"][:500],
            description_short=self._split(row["Company description"], 200),
        )

        image_name = row["Company name"]
        for ch in [" ", ".", "-"]:
            image_name = image_name.replace(ch, "")
        img_file = self.images_path.glob(f"**/logo/{image_name.lower()}.*")
        for file in img_file:
            c.logo = ImageFile(open(file, "rb"))
        c.save()
        return c

    def _create_product(self, row, c, i):
        p = ProductEntry(
            product_name=row["Product name"],
            company=c,
            modified_date=row["Timestamp"],
            short_name=row["Short name"][:50],
            description=row["Product description"][:300],
            description_short=self._split(row["Product description"], 200),
            modality=row["Modality"],
            subspeciality=row["Subspeciality"],
            input_data=row["Input data"],
            file_format_input=row["File format of input data"],
            output_data=row["Output data"],
            file_format_output=row["File format of output data"],
            key_features=row["Key-feature(s)"],
            # key_features_short=_split(row["Key-feature(s)"], 100),
            ce_status=STATUS_MAPPING.get(
                row["CE-certified"], ProductEntry.STATUS_UNKNOWN
            ),
            ce_class=row["If CE-certified, what class"],
            fda_status=STATUS_MAPPING.get(
                row["FDA approval/clearance"], ProductEntry.STATUS_UNKNOWN
            ),
            fda_class=row["If FDA approval/clearance, what class"],
            verified=STATUS_MAPPING.get(
                row["Verified"], ProductEntry.STATUS_UNKNOWN
            ),
            ce_verified=STATUS_MAPPING.get(
                row["CE verified"], ProductEntry.STATUS_UNKNOWN
            ),
            integration=row["Integration"],
            deployment=row["Deployment"],
            process_time=row["Algorithm processing time per study"],
            trigger=row["Trigger for the analysis of data"],
            market_since=str(row["Product on the market since"]),
            countries=str(row["Number of countries present"]),
            distribution=str(
                row["Distribution platforms/marketplaces availability"]
            ),
            institutes_research=str(
                row["Number of institutes using the product for research"]
            ),
            institutes_clinic=str(
                ["Number of institutes using the product in clinical practice"]
            ),
            pricing_model=row["Pricing model"],
            pricing_basis=row["Pricing model based on"],
            tech_peer_papers=row[
                "Name peer reviewed papers that describe the performance of the software as is commercially available."
            ],
            tech_other_papers=row[
                "Name other (white)papers that describe the performance of the software as is commercially available."
            ],
            all_other_papers=row[
                "Name other relevant (white)papers regarding the performance or implementation of the software not mentioned above."
            ],
        )

        p.save()
        p.images.set(i)

        img_file = self.images_path.glob(
            "**/product_images/{}.*".format(row["Short name"].lower())
        )
        for file in img_file:
            p.product_img = ImageFile(open(file, "rb"))

        p.save()
        return p

    def _create_product_images(self, row):
        images = []
        img_files = self.images_path.glob(
            "**/product_images/{}_*.png".format(row["Short name"])
        )
        for file in img_files:
            img = ImageFile(open(file, "rb"))
            i = ProductImage(img=img)
            i.save()
            images.append(i)
        return images
