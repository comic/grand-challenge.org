from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
)


def array_to_string(a):
    if len(a) == 0:
        return "[]"
    return '[\n\t"' + '",\n\t"'.join(map(lambda v: str(v), a)) + '"\n]'


def migrate_annotations(annotations):  # noqa: C901
    translated = 0
    already_translated = 0
    boolean_oct_no_match = []
    enface_no_match = []
    oct_no_match = []
    no_match = []

    paginator = Paginator(annotations, 100)

    print(f"Found {paginator.count} annotations")

    for idx in paginator.page_range:
        print(f"Page {idx} of {paginator.num_pages}")

        page = paginator.page(idx)

        for annotation in page.object_list:
            modality = "enface"
            if (
                annotation.image.modality is not None
                and annotation.image.modality.modality == "OCT"
            ):
                modality = "oct"

            if annotation.name in old_to_boolean_lesion_map:
                if modality == "oct":
                    boolean_oct_no_match.append(annotation.id)
                    continue
                new_name = f"retina::enface::{annotation.name.split('::')[-1]}"
                BooleanClassificationAnnotation.object.create(
                    {
                        "grader": annotation.grader,
                        "created": annotation.created,
                        "image": annotation.image,
                        "name": new_name,
                        "value": True,
                    }
                )
                annotation.delete()
                translated += 1
                continue

            for lesions in old_to_new_lesion_map:
                if annotation.name in lesions[0]:
                    new_name = (
                        lesions[1] if modality == "enface" else lesions[2]
                    )
                    if new_name == "":
                        if modality == "enface":
                            enface_no_match.append(annotation.id)
                        else:
                            oct_no_match.append(annotation.id)
                    else:
                        annotation.name = f"retina::{new_name}"
                        annotation.save()
                        translated += 1
                    break
            else:
                map_idx = 2 if modality == "oct" else 1
                if annotation.name != "" and annotation.name in map(
                    lambda v: f"retina::{v[map_idx]}", old_to_new_lesion_map
                ):
                    already_translated += 1
                else:
                    no_match.append(annotation.id)
    return {
        "translated": translated,
        "already_translated": already_translated,
        "boolean_oct_no_match": boolean_oct_no_match,
        "enface_no_match": enface_no_match,
        "oct_no_match": oct_no_match,
        "no_match": no_match,
    }


class Command(BaseCommand):
    help = (
        "Migrates polygon annotation sets from old lesion items to new items"
    )

    def handle(self, *args, **options):
        annotations = (
            PolygonAnnotationSet.objects.all()
            .order_by("created")
            .select_related("image__modality")
        )
        result = migrate_annotations(annotations)
        print(
            f"Done! {result['translated']}/{len(annotations)} annotations translated, {result['already_translated']} already translated."
        )

        print(
            "boolean_oct_no_match = "
            + array_to_string(result["boolean_oct_no_match"])
        )
        print(
            "oct_no_match = " + array_to_string(result["boolean_oct_no_match"])
        )
        print(
            "enface_no_match = "
            + array_to_string(result["boolean_oct_no_match"])
        )
        print("no_match = " + array_to_string(result["boolean_oct_no_match"]))


old_to_new_lesion_map = [
    (
        (
            "amd_present::Drusen and drusen like structures::Hard Drusen",
            "drusen and drusen like structures::hard drusen",
        ),
        "enface::rf_present::Hard drusen",
        "oct::macular::Drusen",
    ),
    (
        (
            "amd_present::Drusen and drusen like structures::Soft distinct drusen",
            "drusen and drusen like structures::soft distinct drusen",
        ),
        "enface::rf_present::Soft distinct drusen",
        "oct::macular::Drusen",
    ),
    (
        (
            "amd_present::Drusen and drusen like structures::Soft indistinct drusen",
            "drusen and drusen like structures::soft indistinct drusen",
        ),
        "enface::rf_present::Soft indistinct drusen",
        "oct::macular::Drusen",
    ),
    (
        (
            "amd_present::Drusen and drusen like structures::Area with confluent drusen",
        ),
        "enface::rf_present::Area with confluent drusen (no spacing allowed)",
        "oct::macular::Drusen",
    ),
    (
        (
            "amd_present::Drusen and drusen like structures::Reticular Pseudo Drusen",
            "drusen and drusen like structures::reticular pseudo drusen",
        ),
        "enface::rf_present::Area with Reticular Pseudo Drusen",
        "oct::macular::Reticular pseudo drusen",
    ),
    (
        ("amd_present::Drusen and drusen like structures::Conical drusen",),
        "",
        "oct::macular::Conical drusen",
    ),
    (
        (
            "amd_present::Pigment changes & RPE degeneration::Decreased pigmentation/RPE degeneration",
            "pigment changes & rpe degeneration::decreased pigmentation",
            "pigment changes & rpe degeneration::hypopigmentations focal",
            "pigment changes & rpe degeneration::rpe degeneration",
        ),
        "enface::rf_present::Decreased pigmentation/RPE degeneration",
        "oct::macular::RPE degeneration (not atrophy)",
    ),
    (
        (
            "amd_present::Pigment changes & RPE degeneration::Increased pigmentation",
            "pigment changes & rpe degeneration::hyperpigmentations focal",
            "pigment changes & rpe degeneration::increased pigmentation",
        ),
        "enface::rf_present::Increased pigmentation",
        "",
    ),
    (
        (
            "amd_present::Pigment changes & RPE degeneration::Hyperreflective foci in the retina",
        ),
        "",
        "oct::macular::Hyperreflective foci in the retina",
    ),
    (
        (
            "amd_present::Pigment changes & RPE degeneration::Area with mixed decreased/increased pigment",
            "Pigment changes & RPE degeneration::hyper- and hypopigmentations focal",
        ),
        "enface::rf_present::Area with mixed decreased/increased pigment",
        "",
    ),
    (
        (
            "amd_present::Dry end stage::Geographic atrophy",
            "macular",
            "peripapillary",
            "pigment changes & rpe degeneration::geographic atrophy",
        ),
        "enface::rf_present::Geographic atrophy",
        "oct::macular::RPE atrophy (including GA)",
    ),
    (
        ("amd_present::Dry end stage::Retinal Cavitations",),
        "",
        "oct::macular::Retinal cavitation",
    ),
    (
        ("amd_present::Dry end stage::Nascent GA",),
        "",
        "oct::macular::Nascent GA",
    ),
    (
        ("amd_present::Dry end stage::Outer retinal tubulations",),
        "",
        "oct::macular::Outer retinal tubulation",
    ),
    (
        ("amd_present::Wet end stage::Subretinal fluid",),
        "",
        "oct::macular::Subretinal fluid",
    ),
    (
        ("amd_present::Wet end stage::Hard exudates",),
        "enface::rf_present::Hard exudates",
        "oct::macular::Hard exudates",
    ),
    (
        ("dr_present::Hard exudates",),
        "enface::rf_present::Hard exudates",
        "oct::macular::Hard exudates",
    ),
    (
        ("amd_present::Wet end stage::Serous detachment",),
        "enface::rf_present::Retinal serous detachment",
        "oct::myopia::Serous detachment",
    ),
    (
        (
            "amd_present::Wet end stage::Hemorrhage",
            "vascular changes::subretinal hemorrhage",
        ),
        "enface::rf_present::Subretinal hemorrhage",
        "oct::macular::Subretinal hemorrhage",
    ),
    (
        (
            "dr_present::Retinal dot/blot hemorrhages",
            "vascular changes::retinal dot/blot hemorrhages",
        ),
        "enface::rf_present::Retinal dot/blot hemorrhages",
        "oct::macular::Retinal dot/blot hemorrhage",
    ),
    (
        (
            "amd_present::Wet end stage::Fibrous scarring/fibrosis",
            "scars, pits, holes::fibrous scars",
        ),
        "enface::rf_present::Fibrous scarring/fibrosis",
        "oct::macular::Fibrous scarring/fibrosis",
    ),
    (
        ("amd_present::Wet end stage::Supra RPE debris",),
        "",
        "oct::macular::Supra RPE debris",
    ),
    (
        ("dr_present::Laser photocoagulation",),
        "enface::rf_present::Laser photocoagulation",
        "oct::macular::Laser coagulates",
    ),
    (
        ("dr_present::Hemorrhages flame",),
        "enface::rf_present::Flame hemorrhages",
        "",
    ),
    (
        ("dr_present::Cotton wool spots",),
        "enface::rf_present::Cotton wool spots",
        "oct::macular::Cotton wool spot",
    ),
    (("dr_present::Macular edema",), "enface::rf_present::Macular edema", ""),
    (
        ("oda_present::Disc hemorrhage", "vascular changes::disc hemorrhage"),
        "enface::oda_present::Disc hemorrhage",
        "oct::optic_disc::Disc hemorrhage",
    ),
    (
        ("oda_present::Peripapillary atrophy (PPA)",),
        "enface::oda_present::Peripapillary atrophy (PPA)",
        "oct::optic_disc::Peripapillary atrophy (PPA)",
    ),
    (
        ("oda_present::Optic Disk pits",),
        "enface::oda_present::Optic disc pits",
        "oct::optic_disc::Optic disc pit",
    ),
    (
        ("oda_present::Optic Disk drusen",),
        "enface::oda_present::Optic disc drusen",
        "oct::optic_disc::Optic disc drusen",
    ),
    (("oda_present::Tilted disc",), "enface::oda_present::Tilted disc", ""),
    (
        ("oda_present::Papillary edema",),
        "enface::oda_present::Papillary edema",
        "oct::optic_disc::Papillary edema",
    ),
    (
        ("myopia_present::Lacquer cracks",),
        "enface::myopia_present::Lacquer cracks",
        "oct::myopia::Lacquer cracks",
    ),
    (
        ("myopia_present::Diffuse hypopigmentation",),
        "enface::myopia_present::Diffuse hypopigmentation",
        "",
    ),
    (
        ("myopia_present::RPE atrophy",),
        "enface::myopia_present::RPE atrophy",
        "oct::myopia::RPE atrophy",
    ),
    (
        ("myopia_present::RPE hyperpigmentation",),
        "enface::myopia_present::RPE hyperpigmentation",
        "",
    ),
    (
        ("myopia_present::Hard exudates",),
        "enface::myopia_present::Hard exudates",
        "oct::myopia::Hard exudates",
    ),
    (
        ("myopia_present::Subretinal fluid",),
        "",
        "oct::macular::Subretinal fluid",
    ),
    (
        ("myopia_present::Serous detachment",),
        "enface::myopia_present::Serous detachment",
        "oct::myopia::Serous detachment",
    ),
    (
        ("myopia_present::Hemorrhage",),
        "enface::myopia_present::Hemorrhage (myopia)",
        "oct::myopia::Hemorrhage (myopia)",
    ),
    (
        ("myopia_present::Fuchs spot",),
        "enface::myopia_present::Fuchs spot (fibrosis)",
        "oct::myopia::Fuchs spot (fibrosis)",
    ),
    (
        (
            "myopia_present::Myopic peripapilary atrophy (PPA)",
            "vascular changes::myopic peripappilary atrophy",
        ),
        "enface::myopia_present::Myopic peripapilary atrophy (PPA)",
        "oct::myopia::Peripapillary atrophy (PPA, myopia related)",
    ),
    (
        ("myopia_present::Peripapillary Intrachoroidal Cavitation (PICC)",),
        "enface::myopia_present::Peripapillary Intrachoroidal Cavitation (PICC)",
        "oct::myopia::Peripapillary Intrachoroidal Cavitation (PICC)",
    ),
    (
        (
            "other_present::Other::Nevus choroidea",
            "pigment changes & rpe degeneration::nevus choroidea",
        ),
        "enface::rf_present::Nevus choroidea",
        "",
    ),
    (
        (
            "other_present::Other::Chorioretinal scar",
            "scars, pits, holes::chorioretinal scar",
        ),
        "enface::rf_present::Chorioretinal scar",
        "",
    ),
    (
        ("other_present::Other::Tumor, malignant",),
        "enface::rf_present::Tumor unspecified",
        "oct::macular::Tumor unspecified",
    ),
    (
        ("other_present::Other::Myelinated nerve fibres",),
        "enface::rf_present::Myelinated nerve fibres",
        "",
    ),
    (
        (
            "other_present::Vitreo macular::Cellophane maculopathy",
            "drusen and drusen like structures::cellophane maculopathy",
        ),
        "enface::rf_present::Cellophane maculopathy",
        "",
    ),
    (
        (
            "other_present::Vitreo macular::Puckering",
            "scars, pits, holes::puckering",
        ),
        "enface::rf_present::Puckering",
        "",
    ),
    (
        ("cysts_present::Cystoid macular edema (CME)",),
        "",
        "oct::macular::Intraretinal fluid/cysts (including CME)",
    ),
    (
        ("cysts_present::Cysts",),
        "",
        "oct::macular::Intraretinal fluid/cysts (including CME)",
    ),
    (
        (
            "other_present::Vascular::Retinal arteriovenous nicking",
            "vascular changes::retinal arteriovenous nicking",
        ),
        "enface::rf_present::Retinal arteriovenous nicking",
        "",
    ),
    (
        ("other_present::Vitreous::Vitreous hemorrhage",),
        "enface::rf_present::Vitreous hemorrhage",
        "",
    ),
    (
        ("other_present::Vitreous::Mouches volantes/Vitreous floaters",),
        "enface::rf_present::Mouches volantes (vitreous floaters)",
        "oct::macular::Mouches volantes (vitreous floaters)",
    ),
    (
        ("myopia_present::Fibrous scarring/fibrosis",),
        "enface::rf_present::Fibrous scarring/fibrosis",
        "oct::macular::Fibrous scarring/fibrosis",
    ),
    (
        ("vascular changes::aneurysmata",),
        "enface::rf_present::Retinal micro aneurysms",
        "",
    ),
    (
        (
            "other_present::Vitreo macular::Macular (pseudo) hole - Vitreomacular adhesion (VMA)",
        ),
        "enface::rf_present::Macular (pseudo) hole",
        "oct::macular::Vitreomacular adhesion (VMA)",
    ),
    (
        (
            "other_present::Vitreo macular::Macular (pseudo) hole - Vitreomacular traction (VMT)",
        ),
        "enface::rf_present::Macular (pseudo) hole",
        "oct::macular::Vitreomacular traction (VMT)",
    ),
    (
        (
            "other_present::Vitreo macular::Macular (pseudo) hole - Full thickness macular hole",
        ),
        "enface::rf_present::Macular (pseudo) hole",
        "oct::macular::Macular hole",
    ),
    (
        (
            "other_present::Vitreo macular::Macular (pseudo) hole - Lamellar hole",
        ),
        "enface::rf_present::Macular (pseudo) hole",
        "oct::macular::Lamellar hole",
    ),
    # ===================================================
    (("myopia_present::Retinoschisis",), "", ""),  # ?
    (
        ("oda_present::Vertical cup to disc ratio (CDR)",),
        "enface::_present",
        "oct::optic_disc::",
    ),  # remove?
    (
        (
            "dr_present::retinal neovascularization",
            "vascular changes::neo vascularization",
        ),
        "enface::rf_present::",
        "oct::",
    ),  # in db so needed...
]

old_to_boolean_lesion_map = [
    "other_present::Vascular::Branch retinal artery occlusion",
    "other_present::Vascular::Branch retinal vein occlusion",
    "other_present::Vascular::Central retinal artery occlusion",
    "other_present::Vascular::Central retinal vein occlusion",
    "other_present::Vitreous::Asteroid hyalosis/synch scintillans",
]
