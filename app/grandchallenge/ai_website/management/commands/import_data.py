import pandas as pd
from django.core.management import BaseCommand

from grandchallenge.ai_website.models import (
    CompanyEntry,
    ProductBasic,
    ProductEntry,
)


class Command(BaseCommand):
    help = "Reads csv databaslse and creates sqlite database"

    def add_arguments(self, parser):
        parser.add_argument("dir_products", type=str)
        parser.add_argument("dir_companies", type=str)

    def handle(self, *args, **options):
        data_source_p = options.pop("dir_products")
        data_source_c = options.pop("dir_companies")
        df_c = self._read_data(data_source_c)
        df_p = self._read_data(data_source_p)

        for i, c_row in df_c.iterrows():
            c = self._create_company(c_row)
            df_filter = df_p.loc[df_p["Company name"] == c_row["Company name"]]
            for j, p_row in df_filter.iterrows():
                # pb = self._create_product_basic(p_row, c)
                p = self._create_product(p_row, c)
                # c.products.add(p)

    def _read_data(self, data_dir):
        df = pd.read_excel(data_dir)
        return df

    def _create_company(self, row):
        c = CompanyEntry(
            company_name=row["Company name"],
            modified_date=row["Timestamp"],
            website=row["Company website url"],
            founded=row["Founded"],
            hq=row["Head office"],
            email=row["Email address (public)"],
            description=row["Company description"],
        )
        c.save()
        return c

    def _create_product(self, row, c):
        # p = ProductEntry.objects.create(
        p = ProductEntry(
            product_name=row["Product name"],
            company=c,
            modified_date=row["Timestamp"],
            short_name=row["Short name"],
            description=row["Product description"],
            modality=row["Modality"],
            subspeciality=row["Subspeciality"],
            input_data=row["Input data"],
            file_format_input=row["File format of input data"],
            output_data=row["Output data"],
            file_format_output=row["File format of output data"],
            key_features=row["Key-feature(s)"],
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
        try:
            p.save()
            return p
        except:
            pass

    def _create_product_basic(self, row, c):
        p = ProductBasic(
            product_name=row["Product name"],
            company=c,
            modified_date=row["Timestamp"],
            short_name=row["Short name"],
            description=row["Product description"],
            modality=row["Modality"],
            subspeciality=row["Subspeciality"],
            input_data=row["Input data"],
            file_format_input=row["File format of input data"],
            output_data=row["Output data"],
            file_format_output=row["File format of output data"],
            key_features=row["Key-feature(s)"],
        )
        p.save()
        return p


# For company in df_companies:
# c1 = CompanyEntry(company_name=company.name)
# c1.save()
# For product in df_products:
# p1 = ProductEntry(product_name=product.name, company_name= product.company)
# p1.save()
# c = CompanyEntry.objects.get(company_name=p1.company_name)
# c.products.add(p1)
#
#
# c1 = CompanyEntry(company_name=ScreenPoint-Medical)
# c1.save()

# def _create_new_challenge(self, *, src_challenge, dest_name):
#     new_challenge = Challenge(
#         short_name=dest_name,
#         **{f: getattr(src_challenge, f) for f in self.challenge_fields},
#     )
#     new_challenge.full_clean()
#     new_challenge.save()
#     return new_challenge
