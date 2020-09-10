from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.annotations.models import (
    ImageTextAnnotation,
    PolygonAnnotationSet,
)


def array_to_string(a):
    if len(a) == 0:
        return "[]"
    return '[\n\t"' + '",\n\t"'.join(map(lambda v: str(v), a)) + '"\n]'


def migrate_oct_annotations(annotations):  # noqa: C901
    translated_annotations = []
    non_oct = []

    grader_image_keyed_map = {}

    paginator = Paginator(annotations, 100)

    print(f"Found {paginator.count} annotations")

    for idx in paginator.page_range:
        print(f"Page {idx} of {paginator.num_pages}")

        page = paginator.page(idx)

        for annotation in page.object_list:
            if (
                annotation.image.modality is None
                or annotation.image.modality.modality != "OCT"
            ):
                non_oct.append(annotation.id)
                continue

            key = f"{annotation.grader.id}-{annotation.image.pk}"
            grader_image_keyed_map[key] = grader_image_keyed_map.get(
                key, []
            ) + [annotation]

    print("Grader and image keyed map created")
    for annotations in grader_image_keyed_map.values():
        text_annotation, _ = ImageTextAnnotation.objects.get_or_create(
            grader=annotations[0].grader,
            image=annotations[0].image,
            defaults={"text": ""},
        )
        text = "\n\nAnnotations created in legacy workstation:\n"
        for annotation in annotations:
            text += f"- {annotation.singlepolygonannotation_set.count()} annotations named {annotation.name}"
            translated_annotations.append(annotation.id)
            annotation.delete()

        text_annotation.text += text
        text_annotation.save()
        print(
            f"-- For image {annotations[0].image.name} and grader {annotations[0].grader} - {len(annotations)} combined into 1 text annotation"
        )

    return {
        "translated_annotations": translated_annotations,
        "non_oct": non_oct,
    }


class Command(BaseCommand):
    help = (
        "Migrates polygon annotation sets from old lesion items to new items"
    )

    def handle(self, *args, **options):
        annotations = (
            PolygonAnnotationSet.objects.filter(pk__in=oct_no_match)
            .order_by("created")
            .select_related("image__modality")
        )
        result = migrate_oct_annotations(annotations)
        print(
            f"Done! {len(result['translated_annotations'])}/{len(annotations)} annotations translated."
        )
        missed_annotations = list(
            filter(
                lambda a: a not in result["translated_annotations"]
                and a not in result["non_oct"],
                oct_no_match,
            )
        )

        print("missed_annotations = " + array_to_string(missed_annotations))
        print("non_oct = " + array_to_string(result["non_oct"]))


oct_no_match = [
    "a982e19b-8af4-45d0-8dd8-759568eed7fe",
    "44db5fe4-3db2-4488-9800-a95411c5df0d",
    "1fedb9ce-3dde-4317-9915-ba12411a219e",
    "6e3ce13a-36a0-4557-9ffd-458d620038bb",
    "890b02cd-b131-4544-a251-0cbaff32c5e8",
    "17bc0da8-068d-4a8b-be59-7dc6a86825b0",
    "b6b3ad8e-95fa-4969-8f8e-2dde291f3e77",
    "a1980e0e-0778-4dc3-8665-b63513b20e26",
    "cb606222-48d6-4bd7-95b2-38281c5958bb",
    "b9d3932c-7ee0-4ac7-b5e1-103d4effcdca",
    "d9fd5f12-6c04-4b38-a26d-90112dffbccf",
    "27b281b5-f8f6-4ac4-888a-737a82b2d26b",
    "e4efb524-0736-4254-95b0-99afc9ad0e80",
    "75ce5d49-4cb6-47ab-a00b-c6ac15175f9c",
    "60d3aa2c-a00f-4a94-b2ab-5f0d7908ba59",
    "a6750022-a796-4067-ad14-dab5001553e3",
    "f25810fe-5b76-4eb1-802c-c13fa9f07f45",
    "584af70e-f42d-4b35-8dcd-6267b657c1c5",
    "10e2d54e-36dd-4941-87ab-13ec1cce8087",
    "12cd59f7-bcbc-465a-8b03-f0fbad4d29cd",
    "4dcdfe6c-d43b-4119-9fc9-8d422b5ccbd6",
    "90722e82-1436-4995-be88-1125e1bfd66e",
    "3036eee6-b240-45d5-b394-4b432cd4a1dc",
    "01cbdf41-2a97-451f-8384-5593fcbff0d4",
    "71883e53-3722-483f-b9e8-3908054d9632",
    "a972099f-c9d8-4c5d-97aa-fd3df7e7fa2e",
    "16207316-25d5-4c2f-87ec-c1357f3b483f",
    "42c06556-3b94-4abb-96a5-56f7cd8ac634",
    "4d04773b-b1c0-4c76-9cb7-420b870e41bb",
    "4e38234f-654d-4381-847c-564a9b0e27af",
    "080eeebe-6412-480c-a7c2-39f6fbe8ecbc",
    "f36de57a-c7c3-4836-802e-7fc76352d740",
    "075df317-e7c1-4a12-be1c-822898e61fc7",
    "fac970a3-ab94-433c-9aa8-215e5e2222c8",
    "b76c1f5c-e7ac-4a19-92f6-199967002b16",
    "8fa5373c-6de5-4619-b359-6ba1b75e95ac",
    "24ce2de2-5597-4855-8bb3-3d4c91d1fad1",
    "45f0a20f-20fd-4e07-b617-0fdbe64caaea",
    "40ed2d04-11f6-4668-9eaf-6062123d9d37",
    "cc5507c8-b3ec-48cc-8f2d-a34b7877b9fa",
    "35f1fd4f-1ff5-4651-81c5-c5868f425fc2",
    "56f5ca80-cb49-401f-9915-8b424718bb5f",
    "21cc9f7d-b895-45b7-b1d8-56aa541b81eb",
    "22e46a9c-5cef-4bb8-ab8f-77b38ae82df8",
    "361cf7bf-5488-41f1-8171-6423a29335ad",
    "1be3eb23-bc25-414b-b999-c2d74d055679",
    "4ac145a8-b16a-481d-9e7c-0d42983de5b1",
    "3b16dd71-a008-49a8-b5f6-8496ce5ad32f",
    "ac300963-b284-4b02-a9ef-96f017ace9ad",
    "32532b62-4a51-4660-a40f-8c4675cb8cb6",
    "8fe36f59-45a0-4f31-a8df-8dc075005106",
    "997ed360-de58-499d-a95b-8bb42063abfe",
    "17acf658-860a-4e68-9b5c-eb2b7dd32d50",
    "9e02d9ee-f8f9-45c4-ab56-702d97528253",
    "25cb52a7-2723-486f-8740-fb94711972e2",
    "a4ae3bd8-da26-49d7-b200-68769337bd44",
    "b52d6d41-b791-462f-b4c6-97ce2bdd9cc5",
    "5bb701f6-78da-455c-8e4d-f2c9591f3a65",
    "e24badd5-13d6-4aa9-9d7f-6809ac8a36fd",
    "c087490d-3116-4b74-abda-2abed4ea0467",
    "2e071aea-8790-4ba3-a8e1-569acc5730d3",
    "df3d4a11-5a34-4337-91fb-ea5a1f498b08",
    "e942319e-24ff-4e2d-97c0-d26bb8169141",
    "50477108-8730-4467-bbcf-3ee6bb72e534",
    "0434febf-9979-4f69-981f-2836a7fb2579",
    "748a3d1d-15c4-4334-a37d-0dbb0242eff3",
    "f0d4d7bb-213d-4d72-8a81-1ea752586959",
    "8e5e349a-208f-448b-a17b-68f91e0ffec0",
    "f9c6d9b2-9bd8-47a6-9ecd-af23745a1fe0",
    "fb727cd8-d626-44f2-a406-1d1a6de0e2be",
    "37ea595d-0a48-4332-bb68-9e596e3d6273",
    "9733279c-8175-416e-a4cf-4ddc46bd7719",
    "ebb85354-d6a4-4f22-99ae-c0196d48da3e",
    "8fb41767-9ae8-4def-a716-f3cf021e633d",
    "a1205ab1-fcd6-41da-b79a-2e08ff80fa28",
    "e12496df-a422-4bba-824e-bd1312500da5",
    "d401e85d-c087-4d82-840c-f909ad6039c4",
    "a4cc393b-c35f-435a-8d0e-a90f7a6d0814",
    "20873376-7aa7-45f8-89a7-53765e15c796",
    "24598509-4051-4340-a75c-6ed75990be55",
    "8968b7f6-c760-4123-967e-f67b9bb12724",
    "a225188f-b23a-44f0-8718-747733348c33",
    "76d087f8-be64-421b-82dc-d5ace7ae469f",
    "d4259a24-cf11-498b-a546-9c97194bb116",
    "f45f5700-e97e-4279-a8c9-6736ac430e52",
    "fbd71bb1-f3fd-4abe-b584-76a39c6f9d4d",
    "0fbd0834-a3a0-42a9-b351-cff7607df0e3",
    "bf43dc78-5bc8-424c-978c-d4f77eaef4a9",
    "eca486fe-b5f1-45d8-b106-846345dcd83c",
    "b02e3f33-a6c4-40fe-b307-0944a77071d2",
    "24bd7613-1cbb-48a0-ac4c-6f53677b5112",
    "4f883f42-efea-4b40-8d7c-68bb02118ffd",
    "bd25527c-1aab-4019-a197-4afba422db8e",
    "c3caf01c-82bb-4abd-94ed-8d47b5c9a788",
    "923ef921-528c-4387-8d09-e928ecc37afe",
    "0cb4a92c-0f23-421c-a60a-c975aff0c663",
    "f00a8933-c140-4b27-8a8b-2585cc961322",
    "46cfa0d0-ee45-4f22-8108-196940131b21",
    "c3ed4cbf-de3b-4b3f-930c-822979616fcb",
    "7d30b1f4-9810-4f0b-880f-b7e0e0ca33e0",
    "a57fe6db-e93c-4984-b2a2-c16500f4873a",
    "8fcf9a63-61bf-45d6-976c-b95c209faa5a",
    "25ab0cb5-05b0-4f5d-a85f-833f43a6225c",
    "d59540cb-c222-4372-92d5-9f88bbb94406",
    "36c42374-c197-483e-b117-6c98b20fd574",
    "135c7f08-0d92-4aec-bfe4-c20accf54c42",
    "4ad7bbae-6d56-4a3c-9c3a-695748d2ebc7",
    "44c91a28-acd1-4971-af02-a435110fd19a",
    "2fec6daf-b186-46b2-848f-37b150c61a61",
    "8d7e20f9-dc64-4c3d-8d3e-5174734c7583",
    "ed626a4a-fc8a-478a-8337-c8d8f0e42a5b",
    "135006c2-0c70-44e8-b529-45987b7c8c6d",
    "68b8e914-e9f2-4e49-a73c-462f0ce1f87d",
    "4369b7ee-0894-4381-8b8b-fb59b7f75da8",
    "35ae089e-97da-4806-ae6d-a488640d8fb4",
    "e892e4a6-073a-49ad-b06b-ea82670ca734",
    "6a1c9ce2-39d5-4537-9ce8-cd9fd0b8851b",
    "352c47ff-f68f-458e-98b2-3968030f92fd",
    "b51a31de-ae35-4e39-ae5d-d95f9fe0e7a9",
    "003308ea-d118-4cba-9246-467f0358c0bd",
    "1064e8b3-fadd-4521-bfaf-4f9e113ec740",
    "99c14e5a-7312-4a61-a042-d74df2fbee0b",
    "a67f8dba-0c8f-4d33-81cc-e8bc74f3e96b",
    "e3b2520c-8145-4463-ac48-d2564b24a74f",
    "631843af-b5ae-4d6b-8934-0157d6c160c6",
    "decd8f9a-d794-4d46-8d3f-3f82a3caa1ca",
    "2d1fd0f9-523c-477f-9f8e-75bfd82d8cd9",
    "b9dcb5f9-ad70-450d-9b5e-41d6646e9e4b",
    "00c63340-0ebd-4da6-91bd-055bd8391842",
    "f9393727-04ed-48b4-a57b-2abe53023cfa",
    "a1904092-60a5-442b-8cf1-65f88b7f77bb",
    "fea89bac-d2ff-4c6a-993d-46bbf6d69397",
    "93210351-ef51-48e3-87c9-b71c448c9279",
    "2e392bfd-ec35-407a-95e8-2c515e105418",
    "6536b442-ae35-41b2-b7a7-94ac6b5a535c",
    "4289992e-dd6a-41fb-bc8e-b99472a82e9f",
    "aa800e0f-ac9a-47f7-8121-36fb60c0b953",
    "9fd13165-44f6-4410-92e3-34d833deb7c9",
    "a6dd0722-034b-402d-a842-d73c9f4dfba2",
    "dadbb33d-d71f-48b3-9b63-86278d875fe3",
    "1cf25bcf-bdb8-476d-b80d-df737c3c992c",
    "1ca3c13e-b73c-43aa-9a3c-eed93356a40e",
    "42b16b77-c461-4f1d-ad54-725fec4f0419",
    "b2fd7026-2506-401a-abaa-bf38994f2f04",
    "180a1b27-429c-4e14-a8a4-31c64510d45d",
    "aac6d141-28b2-419f-982e-af8e2e2ff1f5",
    "cc11319a-477a-472f-a7a0-feb8c6c5d68a",
    "032ff293-20af-45dd-bf59-4998a4a9936e",
    "eafa4911-33fd-4b23-be41-f2db0d900ccc",
    "13b99fe0-13b7-4ad4-9b06-61a8c8351c7e",
    "7a09c17c-c837-4041-a7c7-fff946c4e937",
    "51b036db-5802-4767-8d19-165769c716fd",
    "b1f0ee9d-1fff-4e5d-a619-ede32d82e89f",
    "d171cdb6-4366-48ef-acfc-0841fcedc829",
    "3154f341-9c2e-494f-b902-93cf835e4087",
    "8c99881b-2f02-4afc-a25d-f63d0eb0ab2c",
    "4f06c0f5-6aeb-4146-b56c-bc117401682c",
    "e2c9176a-1905-4f86-ba9e-51d51b3476dc",
    "13ad4bc6-9cee-444a-97b9-dc09d0cf12c7",
    "16355964-1029-4acd-9ee0-6cd2b864e0b2",
    "fa92fa7a-ff4b-4e2a-b875-3ebd76b4bc07",
    "e76ea625-1523-4915-92bc-3bd00ade878a",
    "5b5d5b89-a843-42ee-9104-df92a9698baa",
    "bb5208bd-250c-433c-91c3-94245d6ddb57",
    "69e397b4-f32d-4f8f-8f97-0c4584afac9f",
    "c02fd61c-3744-4383-ae0a-6030126d76bb",
    "0efaaa45-20ff-442d-88f5-463135d8468b",
    "1c3efa53-fc62-4d7b-bf5b-c46db2de0f3d",
    "e1b8c0b9-de55-424f-a6d9-97032daa2bd9",
    "8cdfeafa-7ffb-43b0-be32-281340ba6410",
    "f33be60b-1481-4c1e-ab0c-67527ad9437d",
    "8f1f4769-924f-4b83-979e-60ebe3f0d19c",
    "c7014693-3c12-4bbd-af01-9e05e20e7fb4",
    "7ce26f5c-dcca-44d1-97ec-845da540f06b",
    "071cd0d1-00e8-414c-9771-51498559548d",
    "ea0f8357-9cc3-4590-a739-c7caaf6b9e6d",
    "c02740a3-f214-4885-b958-0512e4e6e817",
    "a8d4eec6-29ba-4a75-bcb2-1c728c43f1b2",
    "ae11a609-51bc-4f54-acbd-abc709f72b15",
    "89cb37b7-a7f6-406d-a16b-3065d1d91b52",
    "b0b964c4-d096-40df-8bc3-caadb715dab7",
    "d6f8ed90-d4c4-413e-875e-eb92ae7a776b",
    "98d0061e-e547-48b8-85c4-7dcb272160fc",
    "d6e30095-2486-4107-bf7f-a1ea9d7683cc",
    "004e66c2-1e86-4d22-bc83-e5a4206d6fbf",
    "39b13a26-a957-41bf-97a9-93717bc89119",
    "6c962e3e-abdf-4c1d-9169-8ec8fdce582d",
    "2ef9c9c8-6a02-4131-88c0-75a037aaeb8e",
    "b1cdefee-3ad0-429f-b422-26ab7500f829",
    "d7184ef3-9b56-4aa0-80bf-add40658eced",
    "013618df-446c-4d81-a451-67f42cbec679",
    "0868870f-670a-4a81-a228-aa1e8c549cbc",
    "4921cef3-1451-417e-b9ed-ed4438efcc9a",
    "edd698d8-acdc-4090-b2f8-0818094958e7",
    "da92edae-ad6c-48af-8861-cbe127db0b07",
    "1d299e49-7641-4fa5-a68f-85e88bed17a9",
    "828fec45-8002-41b4-af6e-53469b928dcc",
    "ea316a1c-0704-48cb-84df-a728d48a56bf",
    "b587011e-01d9-4325-9be1-9cc984ae1b27",
    "bd00a59c-39e5-4a52-8255-476be6b5ee9c",
    "2fbc794e-71d0-4955-9420-ea26b201970b",
    "629f0679-a6fb-445d-8077-c98ff18c2271",
    "7b440180-191b-466d-8c82-328f69fb2391",
    "9745ee4a-febc-4d85-8e1c-7ece72b0a0cf",
    "cca336e4-d76c-49a5-8775-2aeb2f9f7a08",
    "af27118f-88ff-4987-82cd-c24c83d36284",
    "802c2e54-b501-4994-b7cb-97f75db0607b",
    "d55425df-79c9-49cf-98e5-ea1558cd580c",
    "acb4db06-a7b0-48c1-9a46-8511cf924fc3",
    "ee00c3dc-2e04-43b8-93b2-29b6d23972f2",
    "f5594d26-aff7-417c-bf1a-557c509731e3",
    "d865e7de-feed-4d52-98fc-c36f171a7e3e",
    "93c0f80a-10f0-4a4a-9bc8-dcc608bc1ffd",
    "314f65c4-bc79-4cdb-8efb-f5130150ca90",
    "171ce314-08f0-4b9c-8ff9-92c6dea4d332",
    "d0781882-11ce-4726-9bfc-1fda30959429",
    "6f6aa45e-19a3-465c-9ce5-709a8156d6dc",
    "4921879b-2ad0-48a2-b0ed-88213de8ed7d",
    "9381e964-f157-4586-adbe-5b6fb04e34ac",
    "77fecd4a-d122-44c7-ad55-59e71f01b6ba",
    "e478d4bb-c8c0-4e16-9f7e-81b711f0b621",
    "77eb09ee-02a6-4d70-8707-9029141cbcfe",
    "e3c8ab66-29bd-4324-8fd8-1dc21ce50629",
    "df6eaef0-3ad6-46ee-b8de-4bafe9ec0c64",
    "15306d31-f5dd-4621-ae17-a81360145029",
    "6e09f716-de72-4c53-9bbd-c87d7747d982",
    "8fca20e5-ec6b-466f-9c30-daf2aab1f4ce",
    "82e868b9-64ec-473a-96ef-d062c334f2ff",
    "ee13c212-4b3b-4857-8673-6329e7d8c99c",
    "b1c6cb5b-8a5f-4621-91d0-c22fe17c19be",
    "c34ce1ad-2f8f-40ee-85c3-c355860827e4",
    "24f19344-61cc-440a-8601-d787b31d4b61",
    "ebb6b4c0-ceea-47fa-8bb2-b1a724aaae86",
    "d9e79da3-b4cc-4953-acdf-97bfb55db2a8",
    "8a7e1ba5-1b0b-4a4f-83b7-2b6cdd2a1f88",
    "2134837b-23ac-463d-91f4-3a95c067904a",
    "0af71f77-6f09-426b-a5d6-eb47314f1142",
    "1714db48-2fac-4821-a914-997fd6c708b7",
    "2f4e5a73-13ab-4f29-b133-3f998f0c12f0",
    "8b3aa329-3acd-436c-8632-1ddf48c96405",
    "3f8f6996-5fb1-4329-8a67-9d6e007938d0",
    "c3d484e0-fdc8-4087-8d78-92d7a699ef9f",
    "5627f1d7-aae5-46db-9cd7-5eccee1cd58d",
    "4f24524a-898f-4fb3-a79e-01664b0e9d47",
    "41b8fc2e-070e-49c0-8d3b-ead595d3fa7b",
    "4e24b574-635d-4465-90c0-66112f6ad5a4",
    "c3d4bf39-7d44-430d-b63a-475119c77917",
    "5343bb4a-9770-4fa9-9acb-ea5e5f3a084f",
    "7ccde096-c906-4c04-b80b-52c4f7789560",
    "a0fc637e-9b84-42d5-9bbe-e6775524470a",
    "0a2a52e4-c538-43ca-abf6-107a98233751",
    "f679965b-b46e-4305-a8a8-2cea0a4b5aec",
    "a3cba3c9-08ed-43e4-a0e1-edfe6d054596",
    "48f77b15-0674-4420-b172-c0c1026c705c",
    "7c641785-3be2-454a-a67d-08ff2bddf42b",
    "eaa0ae61-a5f5-4902-92ce-31baaf975e79",
    "4ed69aaa-5c81-4e8a-a23a-b18668f3cc10",
    "337f638c-1be2-4fd5-bb0b-291bfae5eae0",
    "618d6455-abd6-4289-92fb-df033ae9fe0d",
    "2d79e625-fe5d-461d-bafe-80bd9894c6e7",
    "55da72bc-36b8-4633-85e7-8da2a7707857",
    "f2cce9a8-4585-4ebe-ae97-c1af8e2c7c41",
    "9343fd31-f926-46c4-b96e-3bdf5dba7499",
    "cc5adc04-24d0-4f0b-84fb-fe82c32d181c",
    "fa44dae3-e4f1-4d5f-8f55-164477fbbe76",
    "4b3fe62f-33ae-40d0-9832-0eee9cbed8d8",
    "72814a7c-0b74-4ea0-aa62-4f0db309eddd",
    "abc3baa0-a1d7-4a09-b2f5-0fdc7c94ed80",
    "c5c54e1f-416b-4c87-9133-194f0f4b5c11",
    "ddde4a9e-81c0-49be-8c41-32819dddd7b2",
    "4b28432c-9962-4f38-8a1d-cfce6d962b0f",
    "63b58ecc-3720-44b4-a9f9-5614f17f6ed8",
    "bb8e569d-3ea9-407f-9814-534205c9c14e",
    "b96f9fb3-3723-4f47-9996-8e684ebaf554",
    "f9d0ca3f-79c8-49cf-a40b-5d02a2d08a55",
    "8007d051-9dde-4a3f-802f-098f6122ffcf",
    "ce3ceb1d-89bc-4e5f-881d-7a198bec3144",
    "51968869-693c-4e92-a6bf-082c45b1d082",
    "b016b910-58bc-47eb-a8ab-3005ec8362fc",
    "8e805172-b9a6-4bfb-8dd5-e85aab4babbd",
    "3859ece4-a460-4083-9cba-0945a3c892d0",
    "04984c23-7073-4e48-91b6-88ed54f920ec",
    "46b1ab54-d188-4028-809e-0f3f63a5545f",
    "9a2799d3-e472-42b1-a069-7af42cc3bd42",
    "a33e9293-a56c-4bc1-963b-4a40964c8c10",
    "c2665fa4-0552-402f-bf21-042b5463ac64",
    "87a48d0d-7be3-4f60-b517-55581d19c816",
    "df2d23f6-d7c3-4203-954c-ac021240313a",
    "a4e08f31-b501-402b-8d19-3eff9b336c06",
    "5f750641-7569-4733-b587-ea40dfeceffc",
    "3962f0c3-a3be-4cb6-be98-b632ab2c2028",
    "8d1e1acd-746c-48f7-be86-5e7f29aa8eca",
    "e5559598-5957-4ebd-bd3a-14ca3b838177",
    "1268243e-def9-470f-ba5e-d2dae30fd679",
    "74dafa60-b062-4f10-ba41-0a038a969402",
    "bf93ba61-be3b-467a-b50a-87791a28f6ed",
    "66e10730-e706-4551-a3f8-d316ac1a7c57",
    "0c7af59d-285a-4821-99fb-dfc632b6eee3",
    "9e7d39ae-cda9-4a8a-a0d4-2ea7157e7805",
    "f9cf05fb-52dd-4fa4-a3b7-542bb0a84696",
    "b9fd9f32-4f5f-4170-9821-682592c5cda4",
    "ffa0ae7e-4202-4d22-a18c-6e50b9c7898a",
    "d19cc2e8-a6a3-443f-91c1-ecb78055f522",
    "f412d598-0863-4cf0-b3e4-dee46a1cffcf",
    "c8afae93-3bf1-4c9c-bcf3-b39a35f525c8",
    "62eb2325-6eae-4532-bb51-c1b1ee2a749d",
    "f3bd3640-c7d0-4132-ba63-ac3c1623e9f7",
    "6aef5cf2-d79a-43de-af3b-384cedac20cc",
    "d1af627e-9505-413f-844b-5ed8197c57ab",
    "c3d97ac2-29ca-437e-9837-f55bb59bdc29",
    "f17f9379-31b2-44b0-9b37-f82bbb954553",
    "75b74469-3937-416d-b36a-df46173e9078",
    "dcb447af-5ed0-4008-8ef2-715860dc46c0",
    "8b809bfb-2f92-4bf5-96c5-6bb9993a033f",
    "7bf91506-8cce-4845-94e4-e3be68aa1be7",
    "4cdd3618-689f-4fff-a6af-47e4c9ff5113",
    "e327e621-25a6-4631-9505-99c255659abb",
    "23b1b54d-2958-4a54-81c9-cc79dfc9b258",
    "0cb3ba43-d9c7-4475-a120-ba8ab36d74bb",
    "46efdeb2-f4ab-43b2-8bd8-148f0c67486c",
    "c4d97d42-322f-4d5e-84b7-477b3422a72a",
    "43520eb6-a382-41b1-9ca2-cc09f62eb215",
    "c1809b91-2e10-4f3a-b710-246b0eb1de8f",
    "026ad03e-b1dd-4a55-81e8-a763700e5471",
    "a0c76512-6b3a-44ff-9ee1-80e99bdb72b5",
    "cf3d2c5e-2909-4ba5-a128-4dbb3e4e4527",
    "dc9f9eee-c855-4308-a42b-53b44fe0db45",
    "2dcff6da-f7c4-408f-90ea-fffa241f27ff",
    "f6b0ac44-3dee-42b3-b8a7-dbd61da5e884",
    "d7422ed0-618a-4abe-8430-528dbfca824d",
    "a3294b5d-3181-4fb4-b5be-19b6ca5d7b9b",
    "68ed0ebc-d113-4b22-af0b-4667b2ea2f13",
    "e0922649-d854-41f0-a9b7-e3e3f1d08856",
    "83673eac-d860-43e3-9417-e06fc89d1024",
    "33b4ad66-54f2-4abd-89b1-1be237772803",
    "e1c8524b-f4ff-4046-bf4e-fbc2e0ea5764",
    "5f907cb5-3713-4607-a3bc-10797f0fe09c",
    "e7d34f24-bf05-41fa-9eb7-3cb2e2ed95a1",
    "eea37f21-a320-43aa-8e29-63b8034e5a4c",
    "9764891b-92c8-4025-847a-4391199a8780",
    "a75dd4d2-7d58-40c5-beb7-9c7c2e45ce04",
]
