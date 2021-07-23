"""
Tools for importing arXiv ids, modified from https://github.com/manubot/manubot

# BSD-2-Clause Plus Patent License

_Copyright © 2017-2020, Contributors & the Greene Lab at the University of Pennsylvania_

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Subject to the terms and conditions of this license, each copyright holder and
contributor hereby grants to those receiving rights under this license a
perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
(except for failure to satisfy the conditions of this license) patent license
to make, have made, use, offer to sell, sell, import, and otherwise transfer
this software, where such license applies only to those patent claims, already
acquired or hereafter acquired, licensable by such copyright holder or
contributor that are necessarily infringed by:

(a) their Contribution(s) (the licensed copyrights of copyright holders and
non-copyrightable additions of contributors, in source or binary form) alone;
or

(b) combination of their Contribution(s) with the work of authorship to which
such Contribution(s) was added by such copyright holder or contributor, if, at
the time the Contribution is added, such addition causes such combination to
be necessarily infringed. The patent license shall not apply to any other
combinations which include the Contribution.

Except as expressly stated above, no rights or licenses from any copyright
holder or contributor is granted under this license, whether expressly,
by implication, estoppel or otherwise.

DISCLAIMER

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import re
import xml.etree.ElementTree

import requests


def query_arxiv_api(*args, **kwargs):
    response = requests.get(*args, **kwargs)
    response.raise_for_status()
    xml_tree = xml.etree.ElementTree.fromstring(response.text)
    return xml_tree


def date_to_date_parts(date):  # noqaL C901
    """
    Convert a date string or object to a date parts list.
    date: date either as a string (in the form YYYY, YYYY-MM, or YYYY-MM-DD)
        or as a Python date object (datetime.date or datetime.datetime).
    """
    import datetime

    if date is None:
        return None
    if isinstance(date, (datetime.date, datetime.datetime)):
        date = date.isoformat()
    if not isinstance(date, str):
        raise ValueError(f"date_to_date_parts: unsupported type for {date}")
    date = date.strip()
    re_year = r"(?P<year>[0-9]{4})"
    re_month = r"(?P<month>1[0-2]|0[1-9])"
    re_day = r"(?P<day>[0-3][0-9])"
    patterns = [
        f"{re_year}-{re_month}-{re_day}",
        f"{re_year}-{re_month}",
        f"{re_year}",
        ".*",  # regex to match anything
    ]
    for pattern in patterns:
        match = re.match(pattern, date)
        if match:
            break
    date_parts = []
    for part in "year", "month", "day":
        try:
            value = match.group(part)
        except IndexError:
            break
        if not value:
            break
        date_parts.append(int(value))
    if date_parts:
        return date_parts


def get_arxiv_csl(*, arxiv_id):
    """
    Generate a CSL Item for an unversioned arXiv identifier
    using arXiv's OAI_PMH v2.0 API <https://arxiv.org/help/oa>.
    This endpoint does not support versioned `arxiv_id`.
    """
    # XML namespace prefixes
    ns_oai = "{http://www.openarchives.org/OAI/2.0/}"
    ns_arxiv = "{http://arxiv.org/OAI/arXiv/}"

    xml_tree = query_arxiv_api(
        url="https://export.arxiv.org/oai2",
        params={
            "verb": "GetRecord",
            "metadataPrefix": "arXiv",
            "identifier": f"oai:arXiv.org:{arxiv_id}",
        },
        timeout=5,
    )

    # Extract parent XML elements
    (header_elem,) = xml_tree.findall(
        f"{ns_oai}GetRecord/{ns_oai}record/{ns_oai}header"
    )
    (metadata_elem,) = xml_tree.findall(
        f"{ns_oai}GetRecord/{ns_oai}record/{ns_oai}metadata"
    )
    (arxiv_elem,) = metadata_elem.findall(f"{ns_arxiv}arXiv")
    # Set identifier fields
    response_arxiv_id = arxiv_elem.findtext(f"{ns_arxiv}id")

    if arxiv_id != response_arxiv_id:
        raise ValueError(
            f"arXiv oai2 query returned a different arxiv_id:"
            f" {arxiv_id} became {response_arxiv_id}"
        )

    csl_item = {
        "id": arxiv_id,
        "URL": f"https://arxiv.org/abs/{arxiv_id}",
        "number": arxiv_id,
        "container-title": "arXiv",
        "publisher": "arXiv",
        "type": "manuscript",
    }

    # Set title and date
    title = arxiv_elem.findtext(f"{ns_arxiv}title")
    if title:
        csl_item["title"] = " ".join(title.split())
    datestamp = header_elem.findtext(f"{ns_oai}datestamp")

    date_parts = date_to_date_parts(datestamp)
    if date_parts:
        csl_item["issued"] = {"date-parts": [date_parts]}

    # Extract authors
    author_elems = arxiv_elem.findall(f"{ns_arxiv}authors/{ns_arxiv}author")
    authors = list()
    for author_elem in author_elems:
        author = {}
        given = author_elem.findtext(f"{ns_arxiv}forenames")
        family = author_elem.findtext(f"{ns_arxiv}keyname")
        if given:
            author["given"] = given
        if family:
            author["family"] = family
        authors.append(author)

    csl_item["author"] = authors

    abstract = arxiv_elem.findtext(f"{ns_arxiv}abstract")
    if abstract:
        csl_item["abstract"] = (
            abstract.replace("\n", " ").replace("\r", "").strip()
        )

    license = arxiv_elem.findtext(f"{ns_arxiv}license")
    if license:
        csl_item["license"] = (
            license.replace("\n", " ").replace("\r", "").strip()
        )

    doi = arxiv_elem.findtext(f"{ns_arxiv}doi")
    if doi:
        csl_item["DOI"] = doi

    return csl_item
