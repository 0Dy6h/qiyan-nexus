"""PubMed E-utilities client and XML parsers.

Network calls are isolated in ``PubmedClient`` so tests can inject fakes via
``PubmedClient.from_factory``. Parsing is pure stdlib (``xml.etree``).
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import NoReturn, Protocol

import httpx

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubmedServiceError(Exception):
    """Raised when PubMed API calls fail."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = "qiyan-nexus/0.1 (research; contact: dev@local)"
MAX_RESULTS_HARD_CAP = 50


@dataclass(frozen=True)
class PubmedRecord:
    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None


class PubmedFetcher(Protocol):
    def esearch(self, query: str, *, max_results: int) -> list[str]: ...
    def efetch(self, pmids: list[str]) -> list[PubmedRecord]: ...


def parse_esearch_xml(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [id_node.text for id_node in root.findall("./IdList/Id") if id_node.text]


def _extract_author_name(author_node: ET.Element) -> str | None:
    collective = author_node.findtext("CollectiveName")
    if collective:
        return collective.strip()
    last = (author_node.findtext("LastName") or "").strip()
    fore = (author_node.findtext("ForeName") or "").strip()
    if last and fore:
        return f"{last} {fore}"
    return last or fore or None


_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _extract_year(article: ET.Element) -> int | None:
    for path in (
        "./ArticleDate/Year",
        "./Journal/JournalIssue/PubDate/Year",
        "./Journal/JournalIssue/PubDate/MedlineDate",
    ):
        node = article.find(path)
        if node is None or not (node.text and node.text.strip()):
            continue
        text = node.text.strip()
        if text.isdigit():
            return int(text)
        head = text.split()[0].split("-")[0]
        if head.isdigit():
            return int(head)
    return None


def _extract_journal(article: ET.Element) -> str | None:
    title = article.findtext("./Journal/Title")
    if title:
        stripped = title.strip()
        if stripped:
            return stripped
    iso = article.findtext("./Journal/ISOAbbreviation")
    return iso.strip() if iso and iso.strip() else None


def _extract_abstract(article: ET.Element) -> str:
    pieces: list[str] = []
    for node in article.findall("./Abstract/AbstractText"):
        label = node.attrib.get("Label")
        text = "".join(node.itertext()).strip()
        if not text:
            continue
        pieces.append(f"{label}: {text}" if label else text)
    return " ".join(pieces).strip()


def _extract_doi(pubmed_article: ET.Element) -> str | None:
    for node in pubmed_article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if node.attrib.get("IdType") == "doi" and node.text:
            return node.text.strip()
    return None


def _extract_keywords(medline_citation: ET.Element) -> list[str]:
    keywords: list[str] = []
    for node in medline_citation.findall("./KeywordList/Keyword"):
        text = "".join(node.itertext()).strip()
        if text and text not in keywords:
            keywords.append(text)
    return keywords


def parse_efetch_xml(xml_text: str) -> list[PubmedRecord]:
    root = ET.fromstring(xml_text)
    records: list[PubmedRecord] = []
    for pubmed_article in root.findall("./PubmedArticle"):
        medline = pubmed_article.find("./MedlineCitation")
        article = medline.find("./Article") if medline is not None else None
        if medline is None or article is None:
            continue
        pmid_text = medline.findtext("./PMID")
        if not pmid_text:
            continue
        title_node = article.find("./ArticleTitle")
        title = ("".join(title_node.itertext()).strip()) if title_node is not None else ""
        if not title:
            continue
        authors: list[str] = []
        for author_node in article.findall("./AuthorList/Author"):
            name = _extract_author_name(author_node)
            if name:
                authors.append(name)
        records.append(
            PubmedRecord(
                pmid=pmid_text.strip(),
                title=title,
                abstract=_extract_abstract(article),
                authors=authors,
                keywords=_extract_keywords(medline),
                year=_extract_year(article),
                journal=_extract_journal(article),
                doi=_extract_doi(pubmed_article),
            )
        )
    return records


class PubmedClient:
    """Real NCBI E-utilities client. Two synchronous calls per sync: esearch + efetch.

    We stay well under NCBI's 3 req/s ceiling because callers run at most one
    sync per HTTP request. API key (optional) is read from ``NCBI_API_KEY`` env.
    """

    def __init__(
        self,
        *,
        base_url: str = NCBI_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        api_key: str | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._api_key = api_key or os.environ.get("NCBI_API_KEY") or None
        self._user_agent = user_agent

    def _params(self, **extra: str) -> dict[str, str]:
        params = {"db": "pubmed", **extra}
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    def esearch(self, query: str, *, max_results: int) -> list[str]:
        capped = max(1, min(max_results, MAX_RESULTS_HARD_CAP))
        params = self._params(term=query, retmax=str(capped), retmode="xml")
        try:
            with httpx.Client(
                timeout=self._timeout, headers={"User-Agent": self._user_agent}
            ) as client:
                response = client.get(f"{self._base_url}/esearch.fcgi", params=params)
                response.raise_for_status()
                return parse_esearch_xml(response.text)
        except httpx.HTTPError as exc:
            _raise_pubmed_error(exc)

    def efetch(self, pmids: list[str]) -> list[PubmedRecord]:
        cleaned = [pmid for pmid in pmids if pmid]
        if not cleaned:
            return []
        params = self._params(id=",".join(cleaned), rettype="abstract", retmode="xml")
        try:
            with httpx.Client(
                timeout=self._timeout, headers={"User-Agent": self._user_agent}
            ) as client:
                response = client.get(f"{self._base_url}/efetch.fcgi", params=params)
                response.raise_for_status()
                return parse_efetch_xml(response.text)
        except httpx.HTTPError as exc:
            _raise_pubmed_error(exc)


def _raise_pubmed_error(exc: httpx.HTTPError) -> NoReturn:
    """Convert httpx errors to PubmedServiceError with status code extraction."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    raise PubmedServiceError("NCBI API unavailable", status_code=status) from exc


def fetch_pubmed_records(
    query: str, *, max_results: int, fetcher: PubmedFetcher | None = None
) -> list[PubmedRecord]:
    client: PubmedFetcher = fetcher if fetcher is not None else PubmedClient()
    pmids = client.esearch(query, max_results=max_results)
    if not pmids:
        return []
    return client.efetch(pmids)


def iter_record_summary_lines(records: Iterable[PubmedRecord]) -> Iterable[str]:
    for record in records:
        year = str(record.year) if record.year is not None else "?"
        yield f"PMID {record.pmid} · {year} · {record.title}"
