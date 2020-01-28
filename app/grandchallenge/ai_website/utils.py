import glob
import os

import pandas as pd
from django.core.files.images import ImageFile
from django.core.management import BaseCommand

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductBasic,
    ProductEntry,
    ProductImage,
)


def _read_data(data_dir):
    df = pd.read_excel(data_dir)
    df = df.fillna(value="")
    return df


def import_data(product_data, company_data):
    df_c = _read_data(company_data)
    df_p = _read_data(product_data)

    for i, c_row in df_c.iterrows():
        c = _create_company(c_row)
        df_filter = df_p.loc[df_p["Company name"] == c_row["Company name"]]
        for _, p_row in df_filter.iterrows():
            # pb = self._create_product_basic(p_row, c)
            i = _create_product_images(p_row)
            _create_product(p_row, c, i)


def _split(string, max_char):
    if len(string) > max_char:
        short_string = string[:max_char].rsplit(" ", 1)[0] + " ..."
    else:
        return string
    return short_string


def _create_company(row):
    c = CompanyEntry(
        company_name=row["Company name"],
        modified_date=row["Timestamp"],
        website=row["Company website url"],
        founded=row["Founded"],
        hq=row["Head office"],
        email=row["Email address (public)"],
        description=row["Company description"],
        description_short=_split(row["Company description"], 200),
    )

    image_name = row["Company name"]
    for ch in [" ", ".", "-"]:
        image_name = image_name.replace(ch, "")
    img_file = glob.glob(f"products/media/logo/{image_name}.*")
    if img_file:
        if os.path.isfile(img_file[0]):
            c.logo = ImageFile(open(img_file[0], "rb"))

    c.save()
    return c


def _create_product(row, c, i):
    p = ProductEntry(
        # verified=row["Verified"],
        product_name=row["Product name"],
        company=c,
        # images=i,
        modified_date=row["Timestamp"],
        short_name=row["Short name"],
        description=row["Product description"],
        description_short=_split(row["Product description"], 200),
        modality=row["Modality"],
        subspeciality=row["Subspeciality"],
        input_data=row["Input data"],
        file_format_input=row["File format of input data"],
        output_data=row["Output data"],
        file_format_output=row["File format of output data"],
        key_features=row["Key-feature(s)"],
        # key_features_short=_split(row["Key-feature(s)"], 100),
        ce_status=row["CE-certified"],
        ce_class=row["If CE-certified, what class"],
        fda_status=row["FDA approval/clearance"],
        fda_class=row["If FDA approval/clearance, what class"],
        integration=row["Integration"],
        hosting=row["Hosting"],
        hardware=row["Hardware requirements"],
        market_since=str(row["Product on the market since"]),
        countries=str(row["Number of countries present"]),
        distribution=str(row["Distribution platforms or partners"]),
        institutes_research=str(
            row["Number of institutes using the product for research"]
        ),
        institutes_clinic=str(
            ["Number of institutes using the product in clinical practice"]
        ),
        pricing_model=row["Pricing model"],
        pricing_basis=row["Pricing model based on"],
        tech_papers=row[
            "Name relevant (white)papers regarding the performance of the software (analytical validation)"
        ],
        clin_papers=row[
            "Name relevant (white)papers regarding the implementation of the software (clinical validation)"
        ],
    )
    p.save()
    p.images.set(i)

    img_file = glob.glob(
        "products/media/product_images/{}.*".format(row["Short name"])
    )
    if img_file:
        if os.path.isfile(img_file[0]):
            p.product_img = ImageFile(open(img_file[0], "rb"))

    # if p.ce_status == "Certified":
    #     p.ce_status_icon = "images/icon_check.png"
    # elif p.ce_status == "No or not yet":
    #     p.ce_status_icon = "images/icon_no.png"
    # elif p.ce_status == "Not applicable":
    #     p.ce_status_icon = "images/icon_na.png"
    # else:
    #     p.ce_status_icon = "images/icon_question.png"

    # if (
    #     p.fda_status == "510(k) cleared"
    #     or p.fda_status == "de novo 510(k) cleared"
    #     or p.fda_status == "PMA approved"
    # ):
    #     p.fda_status_icon = "images/icon_check.png"
    # elif p.fda_status == "No or not yet":
    #     p.fda_status_icon = "images/icon_no.png"
    # elif p.fda_status == "Not applicable":
    #     p.fda_status_icon = "images/icon_na.png"
    # else:
    #     p.fda_status_icon = "images/icon_question.png"

    # if p.verified == "Yes":
    #     p.verified_icon = "images/icon_check.png"
    # else:
    #     p.verified_icon = "images/icon_no.png"

    p.save()
    return p


def _create_product_basic(row, c):
    p = ProductBasic(
        product_name=row["Product name"],
        company=c,
        modified_date=row["Timestamp"],
        short_name=row["Short name"],
        description=row["Product description"],
        description_short=_split(row["Product description"], 200),
        modality=row["Modality"],
        subspeciality=row["Subspeciality"],
        input_data=row["Input data"],
        file_format_input=row["File format of input data"],
        output_data=row["Output data"],
        file_format_output=row["File format of output data"],
        key_features=row["Key-feature(s)"],
        key_features_short=_split(row["Key-feature(s)"], 75),
        verified=row["Verified"],
    )

    if p.verified == "Yes":
        p.verified_icon = "images/icon_check.png"
    else:
        p.verified_icon = "images/icon_no.png"
    p.save()
    return p


def _create_product_images(row):
    images = []
    for k in range(1, 10):
        img_file = "products/media/product_images/{}_{}.png".format(
            row["Short name"], k
        )
        if os.path.isfile(img_file):
            img = ImageFile(open(img_file, "rb"))
            i = ProductImage(img=img)
            i.save()
            images.append(i)
    return images
