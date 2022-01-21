"""
FROM: https://github.com/alphagov/govuk-intent-detector/blob/main/src/make_data/make_topology_matrix.py
"""

import re
import pandas as pd
from urllib.parse import urlparse
from typing import Union, List, Dict, Optional
from pathlib import Path, PurePosixPath
from bs4 import BeautifulSoup, SoupStrainer
from bs4.element import Doctype


def clean_url(url: str) -> Union[str, None]:
    """
    Strip schema and main domain from gov.uk pages (e.g., 'https://www.gov.uk/pageA'
    to '/pageA' and 'https://www.gov.uk/' to '/').
    If cross-domain or external urls, return null.
    General structure of a URL: scheme://netloc/path;parameters?query#fragment
    Args:
        url: url string
    Returns:
        The processed url or None.
    """

    parsed = urlparse(url)

    # remove schema and domain from https://gov.uk urls that still have it specified
    if parsed.netloc == 'www.gov.uk':
        if parsed.path == '':
            return '/'
        else:
            return parsed.path if parsed.fragment == '' else parsed.path + '#' + parsed.fragment

    # cross-domain and external urls, mailto addresses, which have scheme (e.g., https://) specified
    if parsed.scheme != '':
        return None
    else:
        return url


def combine_anchor2url(possible_anchor: str, main_url: str) -> str:
    """Attached anchor to the main_url"""

    return possible_anchor if (not possible_anchor) or (
        not possible_anchor.startswith("#")) else main_url + possible_anchor


def process_page_links(
        page_links: Dict[str, List[Optional[str]]]) -> Dict[str, List[str]]:
    """
    Process the hyperlinks in a page by:
    - removing duplicates
    - combining anchor and origin url (e.g., "#section1" to "origin_url#section1)
    - removing schema and main domain ("www.gov.uk") from gov.uk urls
    - removing cross-domain or external urls.
    Args:
        page_links: A dictionary where the key is a page url, and the value is a List of the page's
                    embedded hyperlinks (as string).
    Returns:
        A dictionary of where the key is the page url from ``page_links``, and the value is the List of
        the page's embedded hyperlinks that have been processed as above.
    """
    return {
        page: list(
            set(
                filter(None, [
                    combine_anchor2url(clean_url(link), page) for link in links
                ])))
        for page, links in page_links.items()
    }


def create_topology_matrix_pd(
        page_links: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Generate the adjacency topology matrix from a dictionary where the key is the 'source url' and
    the value is a list of the url's embedded links (a.k.a. destination urls) that are also 'source urls'.
    Args:
        page_links: A dictionary where the key is a page url, and the value is a List of the page's
                    embedded hyperlinks (a.k.a. destination urls)
    Returns:
        A pandas.DataFrame representing the directed adjacency topology matrix.
    """

    edges = [(page, link) for page, links in page_links.items()
             for link in links if link in page_links.keys()]

    df = pd.DataFrame(edges)

    adjacency_matrix = pd.crosstab(df[0], df[1], dropna=False)

    # add columns for unlinked source urls
    columns_to_add = [
        ind for ind in adjacency_matrix.index.values
        if ind not in adjacency_matrix.columns
    ]
    adjacency_matrix = adjacency_matrix.assign(
        **dict.fromkeys(columns_to_add, 0))
    order_of_columns = adjacency_matrix.index.values
    adjacency_matrix = adjacency_matrix[order_of_columns]

    adjacency_matrix.columns.name = None
    adjacency_matrix.index.name = None

    return adjacency_matrix


# Define a function to be iterated over HTML_FILES in parallel
def ingest_html(file_info: Dict[str, Path]) -> Dict[str, List[str]]:
    """
    Ingest the hyperlinks in a page and write them to a dictionary, with the
    name of the page as the key.
    Args:
        file_info: A single-item dictionary, key=URL, value=Path to file.
    Returns:
        A single-item dictionary, key=URL, value = list of more URLs linked to
    """

    page_hyperlinks_dict = {}

    for page_url, filepath in file_info.items():
        with open(filepath, mode="r", encoding="utf-8") as f:
            links = BeautifulSoup(
                f.read(),
                parse_only=SoupStrainer('a'),
                features="lxml"
            )
            hrefs = [
                link.get('href')
                for link in links
                if not isinstance(link, Doctype)
            ]
            page_hyperlinks_dict[page_url] = [
                url
                for url in hrefs
                if (
                    url is not None
                ) and (
                    not url.startswith("#")  # page links to itself
                )
            ]

    return page_hyperlinks_dict


def process_links(links: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Convert URLs into a standard form.
        - Remove fragments `#`
        - Remove parameters `?` such as search terms and step-by-step-nav IDs.
          For some step-by-step pages, such as
          https://www.gov.uk/set-up-business-partnership?step-by-step-nav=37e4c035-b25c-4289-b85c-c6d36d11a763,
          removing the step-by-step-nav parameter causes the page to be
          rendered differently.
        - Remove `https://gov.uk`
        - Make the homepage into `/`
        - Omit non-gov.uk domains (including <something>.gov.uk)
        - Omit duplicates
        - Keep links between a page and itself
    Args:
        links: A single-item dictionary, key=URL, value=List of URLs linked to
    Returns:
        A single-item dictionary, key=URL, value=List of standardised URLs
    """

    results = {}

    for page_url, links_list in links.items():

        # strip fragments and/or parameters
        links_list_proc = [re.split('[#?]', link)[0] for link in links_list]

        # remove external and cross-domain links, clean schema from gov.uk urls
        # (also remove None results)
        links_list_proc = list(
            filter(None, [clean_url(link) for link in links_list_proc])
        )

        # remove special edge cases and omit duplicates
        links_list_proc = list(set([
            link for link in links_list_proc if PurePosixPath(link).stem not in
            ['preview', 'y', 'results', 'questions']
        ]))

        # enter the modified URLs into a dictionary.  Even if there are no
        # links, entering the key means that the page will be represented in
        # the topology matrix
        results[page_url] = links_list_proc

    return results
    