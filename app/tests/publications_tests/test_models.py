import pytest

from grandchallenge.publications.models import Publication

TEST_DOI = "10.1002/mrm.25227"
TEST_CITEPROC_JSON = {
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


@pytest.mark.django_db
def test_metadata_extraction_and_update():
    publication = Publication.objects.create(
        doi=TEST_DOI, citeproc_json=TEST_CITEPROC_JSON
    )

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

    publication.citeproc_json["is-referenced-by-count"] = 100
    publication.save()

    assert publication.referenced_by_count == 100
