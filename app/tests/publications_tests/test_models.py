import pytest

from grandchallenge.publications.models import Publication
from grandchallenge.publications.utils.manubot import get_arxiv_csl

TEST_DOI = "10.1002/mrm.25227"
TEST_CSL = {
    "DOI": "10.1002/mrm.25227",
    "URL": "http://dx.doi.org/10.1002/mrm.25227",
    "ISSN": ["0740-3194"],
    "link": [
        {
            "URL": "https://api.wiley.com/onlinelibrary/tdm/v1/articles/10.1002%2Fmrm.25227",
            "content-type": "application/pdf",
            "content-version": "vor",
            "intended-application": "text-mining",
        },
        {
            "URL": "https://api.wiley.com/onlinelibrary/tdm/v1/articles/10.1002%2Fmrm.25227",
            "content-type": "unspecified",
            "content-version": "vor",
            "intended-application": "text-mining",
        },
        {
            "URL": "http://onlinelibrary.wiley.com/wol1/doi/10.1002/mrm.25227/fullpdf",
            "content-type": "unspecified",
            "content-version": "vor",
            "intended-application": "similarity-checking",
        },
    ],
    "page": "1085-1094",
    "type": "article-journal",
    "issue": "3",
    "score": 1.0,
    "title": "An optimized design to reduce eddy current sensitivity in velocity-selective arterial spin labeling using symmetric BIR-8 pulses",
    "author": [
        {
            "given": "Jia",
            "family": "Guo",
            "sequence": "first",
            "affiliation": [
                {
                    "name": "Department of Bioengineering; University of California, San Diego; La Jolla California USA"
                }
            ],
        },
        {
            "given": "James A.",
            "family": "Meakin",
            "sequence": "additional",
            "affiliation": [
                {
                    "name": "Centre for Functional Magnetic Resonance Imaging of the Brain, Nuffield Department of Clinical Neurosciences; University of Oxford; Oxford United Kingdom"
                }
            ],
        },
        {
            "given": "Peter",
            "family": "Jezzard",
            "sequence": "additional",
            "affiliation": [
                {
                    "name": "Centre for Functional Magnetic Resonance Imaging of the Brain, Nuffield Department of Clinical Neurosciences; University of Oxford; Oxford United Kingdom"
                }
            ],
        },
        {
            "given": "Eric C.",
            "family": "Wong",
            "sequence": "additional",
            "affiliation": [
                {
                    "name": "Department of Radiology; University of California, San Diego; La Jolla California USA"
                },
                {
                    "name": "Department of Psychiatry; University of California, San Diego; La Jolla California USA"
                },
            ],
        },
    ],
    "funder": [
        {
            "DOI": "10.13039/501100000289",
            "name": "Cancer Research UK",
            "award": [],
            "doi-asserted-by": "crossref",
        },
        {
            "DOI": "10.13039/501100000266",
            "name": "Engineering and Physical Sciences Research Council",
            "award": [],
            "doi-asserted-by": "crossref",
        },
        {"name": "NIH", "award": ["R01 EB002096"]},
    ],
    "issued": {"date-parts": [[2014, 4, 7]]},
    "member": "311",
    "prefix": "10.1002",
    "source": "Crossref",
    "volume": "73",
    "created": {
        "date-time": "2014-04-07T13:12:57Z",
        "timestamp": 1396876377000,
        "date-parts": [[2014, 4, 7]],
    },
    "indexed": {
        "date-time": "2020-07-30T01:55:02Z",
        "timestamp": 1596074102796,
        "date-parts": [[2020, 7, 30]],
    },
    "license": [
        {
            "URL": "http://doi.wiley.com/10.1002/tdm_license_1.1",
            "start": {
                "date-time": "2014-04-07T00:00:00Z",
                "timestamp": 1396828800000,
                "date-parts": [[2014, 4, 7]],
            },
            "delay-in-days": 0,
            "content-version": "tdm",
        },
        {
            "URL": "http://onlinelibrary.wiley.com/termsAndConditions#vor",
            "start": {
                "date-time": "2014-04-07T00:00:00Z",
                "timestamp": 1396828800000,
                "date-parts": [[2014, 4, 7]],
            },
            "delay-in-days": 0,
            "content-version": "vor",
        },
    ],
    "subject": ["Radiology Nuclear Medicine and imaging"],
    "language": "en",
    "relation": {"cites": []},
    "subtitle": [
        "Reduced EC Sensitivity in VSASL Using Symmetric BIR-8 Pulses"
    ],
    "deposited": {
        "date-time": "2020-06-29T17:41:36Z",
        "timestamp": 1593452496000,
        "date-parts": [[2020, 6, 29]],
    },
    "publisher": "Wiley",
    "short-title": [],
    "journal-issue": {
        "issue": "3",
        "published-print": {"date-parts": [[2015, 3]]},
    },
    "content-domain": {"domain": [], "crossmark-restriction": False},
    "original-title": [],
    "container-title": "Magnetic Resonance in Medicine",
    "published-print": {"date-parts": [[2015, 3]]},
    "reference-count": 30,
    "published-online": {"date-parts": [[2014, 4, 7]]},
    "references-count": 30,
    "container-title-short": "Magn. Reson. Med.",
    "is-referenced-by-count": 14,
}

TEST_CONSORTIUM_JSON = {
    "indexed": {
        "date-parts": [[2020, 9, 18]],
        "date-time": "2020-09-18T05:43:50Z",
        "timestamp": 1600407830703,
    },
    "reference-count": 0,
    "publisher": "American Medical Association (AMA)",
    "issue": "22",
    "content-domain": {"domain": [], "crossmark-restriction": False},
    "published-print": {"date-parts": [[2017, 12, 12]]},
    "DOI": "10.1001/jama.2017.14585",
    "type": "article-journal",
    "created": {
        "date-parts": [[2017, 12, 12]],
        "date-time": "2017-12-12T20:31:15Z",
        "timestamp": 1513110675000,
    },
    "page": "2199",
    "source": "Crossref",
    "is-referenced-by-count": 556,
    "title": "Diagnostic Assessment of Deep Learning Algorithms for Detection of Lymph Node Metastases in Women With Breast Cancer",
    "prefix": "10.1001",
    "volume": "318",
    "author": [
        {
            "given": "Babak",
            "family": "Ehteshami Bejnordi",
            "sequence": "first",
            "affiliation": [
                {
                    "name": "Diagnostic Image Analysis Group, Department of Radiology and Nuclear Medicine, Radboud University Medical Center, Nijmegen, the Netherlands"
                }
            ],
        },
        {
            "name": "and the CAMELYON16 Consortium",
            "sequence": "additional",
            "affiliation": [],
        },
    ],
    "member": "10",
    "container-title": "JAMA",
    "original-title": [],
    "language": "en",
    "link": [
        {
            "URL": "http://jama.jamanetwork.com/article.aspx?doi=10.1001/jama.2017.14585",
            "content-type": "unspecified",
            "content-version": "vor",
            "intended-application": "similarity-checking",
        }
    ],
    "deposited": {
        "date-parts": [[2017, 12, 12]],
        "date-time": "2017-12-12T20:31:15Z",
        "timestamp": 1513110675000,
    },
    "score": 1.0,
    "subtitle": [],
    "short-title": [],
    "issued": {"date-parts": [[2017, 12, 12]]},
    "references-count": 0,
    "journal-issue": {
        "published-print": {"date-parts": [[2017, 12, 12]]},
        "issue": "22",
    },
    "URL": "http://dx.doi.org/10.1001/jama.2017.14585",
    "relation": {
        "has-review": [
            {
                "id-type": "doi",
                "id": "10.3410/f.732283043.793567347",
                "asserted-by": "object",
            }
        ]
    },
    "ISSN": ["0098-7484"],
    "container-title-short": "JAMA",
}


@pytest.mark.django_db
def test_metadata_extraction_and_update():
    publication = Publication.objects.create(identifier=TEST_DOI, csl=TEST_CSL)

    assert (
        publication.title
        == "An optimized design to reduce eddy current sensitivity in velocity-selective arterial spin labeling using symmetric BIR-8 pulses"
    )
    assert publication.year == 2014
    assert publication.referenced_by_count == 14
    assert (
        publication.ama_html
        == "Guo J, Meakin JA, Jezzard P, Wong EC. An optimized design to reduce eddy current sensitivity in velocity-selective arterial spin labeling using symmetric BIR-8 pulses. <i>Magn Reson Med</i>. 2014;73(3):1085-1094."
    )

    publication.csl["is-referenced-by-count"] = 100
    publication.save()

    assert publication.referenced_by_count == 100


@pytest.mark.django_db
def test_consortium_json():
    publication = Publication.objects.create(
        identifier=TEST_DOI, csl=TEST_CONSORTIUM_JSON
    )
    assert (
        publication.ama_html
        == "Ehteshami Bejnordi B, and the CAMELYON16 Consortium. Diagnostic Assessment of Deep Learning Algorithms for Detection of Lymph Node Metastases in Women With Breast Cancer. <i>JAMA</i>. 2017;318(22):2199."
    )


TEST_ARXIV_CSL = {
    "id": "2006.12449",
    "URL": "https://arxiv.org/abs/2006.12449",
    "number": "2006.12449",
    "container-title": "arXiv",
    "publisher": "arXiv",
    "type": "manuscript",
    "title": "A Baseline Approach for AutoImplant: the MICCAI 2020 Cranial Implant Design Challenge",
    "license": "http://arxiv.org/licenses/nonexclusive-distrib/1.0/",
}


def test_arxiv_to_citeproc(mocker):
    mocker.patch(
        "tests.publications_tests.test_models.get_arxiv_csl",
        return_value=TEST_ARXIV_CSL,
    )
    csl = get_arxiv_csl(arxiv_id="2006.12449")

    assert (
        csl["title"]
        == "A Baseline Approach for AutoImplant: the MICCAI 2020 Cranial Implant Design Challenge"
    )


TEST_ARXIV_JSON = {
    "id": "2006.12449",
    "URL": "https://arxiv.org/abs/2006.12449",
    "number": "2006.12449",
    "container-title": "arXiv",
    "publisher": "arXiv",
    "type": "manuscript",
    "title": "A Baseline Approach for AutoImplant: the MICCAI 2020 Cranial Implant Design Challenge",
    "issued": {"date-parts": [[2020, 6, 25]]},
    "author": [
        {"given": "Jianning", "family": "Li"},
        {"given": "Antonio", "family": "Pepe"},
        {"given": "Christina", "family": "Gsaxner"},
        {"given": "Gord", "family": "von Campe"},
        {"given": "Jan", "family": "Egger"},
    ],
    "abstract": "In this study, we present a baseline approach for AutoImplant (https://autoimplant.grand-challenge.org/) - the cranial implant design challenge, which, as suggested by the organizers, can be formulated as a volumetric shape learning task. In this task, the defective skull, the complete skull and the cranial implant are represented as binary voxel grids. To accomplish this task, the implant can be either reconstructed directly from the defective skull or obtained by taking the difference between a defective skull and a complete skull. In the latter case, a complete skull has to be reconstructed given a defective skull, which defines a volumetric shape completion problem. Our baseline approach for this task is based on the former formulation, i.e., a deep neural network is trained to predict the implants directly from the defective skulls. The approach generates high-quality implants in two steps: First, an encoder-decoder network learns a coarse representation of the implant from down-sampled, defective skulls; The coarse implant is only used to generate the bounding box of the defected region in the original high-resolution skull. Second, another encoder-decoder network is trained to generate a fine implant from the bounded area. On the test set, the proposed approach achieves an average dice similarity score (DSC) of 0.8555 and Hausdorff distance (HD) of 5.1825 mm. The code is publicly available at https://github.com/Jianningli/autoimplant.",
    "license": "http://arxiv.org/licenses/nonexclusive-distrib/1.0/",
}


@pytest.mark.django_db
def test_arxiv_json_citation():
    publication = Publication.objects.create(
        identifier=TEST_ARXIV_JSON["number"], csl=TEST_ARXIV_JSON
    )
    assert (
        publication.ama_html
        == "Li J, Pepe A, Gsaxner C, von Campe G, Egger J. A Baseline Approach for AutoImplant: the MICCAI 2020 Cranial Implant Design Challenge. <i>arXiv</i>. Published online June 25, 2020."
    )
    assert publication.year == 2020
    assert (
        publication.title
        == "A Baseline Approach for AutoImplant: the MICCAI 2020 Cranial Implant Design Challenge"
    )
    assert publication.referenced_by_count is None
