"""Parse search results HTML into structured discovery page objects."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup

from core.dates import parse_deadline, parse_publication_date
from core.exceptions import HtmlParsingError
from core.models import Tender

logger = logging.getLogger(__name__)


@dataclass
class SearchCriteria:
    """Search parameters for discovering tenders."""
    keyword: str | None = None
    buyer: str | None = None
    organization: str | None = None
    publication_date_from: date | None = None
    publication_date_to: date | None = None

    def __post_init__(self) -> None:
        if (
            self.publication_date_from
            and self.publication_date_to
            and self.publication_date_from > self.publication_date_to
        ):
            raise ValueError("publication_date_from must be <= publication_date_to")



@dataclass
class SearchResultPage:
    """Represents a page of discovery results."""

    tenders: list[Tender] = field(default_factory=list)
    current_page: int | None = None
    total_pages: int | None = None
    page_size: int | None = None
    total_results: int | None = None


class SearchResultParser:
    """Parse HTML returned by the discovery client into structured result pages."""

    def parse(self, html: str) -> SearchResultPage:
        """Parse discovery search HTML and return a structured page object."""
        if not html:
            raise HtmlParsingError("Received empty HTML response")

        soup = BeautifulSoup(html, "html.parser")
        rows = self.extract_rows(soup)
        tenders = [self.extract_tender(row) for row in rows]
        pagination = self.extract_pagination(soup)

        return SearchResultPage(
            tenders=[tender for tender in tenders if tender is not None],
            current_page=pagination.get("current_page"),
            total_pages=pagination.get("total_pages"),
            total_results=pagination.get("total_results"),
        )

    def extract_rows(self, soup: BeautifulSoup) -> list[Any]:
        """Extract tender rows, identified by the presence of the cons_ref data cell.
        """
        tds = soup.find_all("td", headers="cons_ref")
        rows = []
        for td in tds:
            row = td.find_parent("tr")
            if row is None or row.find_all("th") != []:
                continue
            rows.append(row)
        return rows

    def extract_tender(self, row: Any) -> Tender | None:
        """Convert a table row into a Tender object."""
        if row is None:
            return None

        ref_cell = row.find("td", headers="cons_ref")
        if ref_cell is None:
            return None

        tender = Tender()
        tender.tender_id = self._extract_hidden_value(row, "refCons")
        tender.organization_acronym = self._extract_hidden_value(row, "orgCons")
        tender.procurement_type = self._extract_by_id_suffix(ref_cell, "type_procedure")
        tender.category = self._extract_by_id_suffix(ref_cell, "panelBlocCategorie")
        tender.publication_date = self._extract_publication_date(ref_cell)
        tender.reference_number = self._extract_reference_number(row)
        tender.tender_object = self._extract_labeled_block(row, "panelBlocObjet")
        tender.public_buyer = self._extract_labeled_block(row, "panelBlocDenomination")
        tender.location = self._extract_location(row)
        tender.deadline = self._extract_deadline(row)
        return tender

    def extract_pagination(self, soup: BeautifulSoup) -> dict[str, int | None]:
        """Extract pagination metadata from the page-size/page-number control widget.

        The site renders this widget twice (Top and Bottom variants share the same
        structure, e.g. numPageTop/numPageBottom), so ids are matched by suffix.
        """
        current_page = self._to_int(
            self._extract_attr_by_id_suffix(soup, r"numPageTop$", "value")
        )
        total_pages = self._to_int(
            self._extract_text_by_id_suffix(soup, r"nombrePageTop$")
        )
        total_results = self._to_int(
            self._extract_text_by_id_suffix(soup, r"nombreElement$")
        )

        return {
            "current_page": current_page,
            "total_pages": total_pages,
            "total_results": total_results,
        }

    def _extract_hidden_value(self, row: Any, name_suffix: str) -> str | None:
        """Read the value of a hidden <input> whose name ends with the given suffix."""
        input_tag = row.find("input", attrs={"name": re.compile(re.escape(name_suffix) + r"$")})
        if input_tag is None:
            return None
        value = input_tag.get("value")
        return value if value else None

    def _find_by_id_suffix(self, container: Any, id_suffix: str) -> Any:
        """Find a descendant whose id ends with the given suffix.

        No separator (e.g. underscore) is required before the suffix, since the
        live site prefixes generated control ids (ctl0_..._panelBlocX) while
        simpler markup (tests, other pages) may use the bare id directly.
        """
        return container.find(id=re.compile(re.escape(id_suffix) + r"$"))

    def _extract_by_id_suffix(self, container: Any, id_suffix: str) -> str | None:
        """Generic helper: find a descendant whose id ends with the given suffix and clean its text."""
        node = self._find_by_id_suffix(container, id_suffix)
        return self._clean_text(node) if node is not None else None

    def _extract_publication_date(self, ref_cell: Any) -> date | None:
        """The publication date is a bare <div>DD/MM/YYYY</div> with no id/class."""
        date_pattern = re.compile(r"\d{2}/\d{2}/\d{4}")
        for div in ref_cell.find_all("div", recursive=False):
            text = self._clean_text(div)
            if text and date_pattern.fullmatch(text):
                return parse_publication_date(text)
        return None

    def _extract_reference_number(self, row: Any) -> str | None:
        """Reference number is held in a <span class="ref"> element."""
        ref_span = row.find("span", class_="ref")
        return self._clean_text(ref_span) if ref_span is not None else None

    def _extract_labeled_block(self, row: Any, id_suffix: str) -> str | None:
        """Extract text from a block like '<strong>Label:</strong> value', stripping the label."""
        block = self._find_by_id_suffix(row, id_suffix)
        if block is None:
            return None
        label = block.find("strong")
        label_text = self._clean_text(label) if label is not None else None
        full_text = self._clean_text(block)
        if full_text and label_text:
            full_text = full_text.replace(label_text, "", 1).strip(" :\u00a0")
        return full_text or None

    def _extract_location(self, row: Any) -> str | None:
        """Location block may repeat itself in a hidden tooltip; take just the first line."""
        block = self._find_by_id_suffix(row, "panelBlocLieuxExec")
        if block is None:
            return None
        direct_strings = [s.strip() for s in block.find_all(string=True, recursive=False) if s.strip()]
        if direct_strings:
            return re.sub(r"\s+", " ", direct_strings[0]).strip() or None
        return self._clean_text(block)

    def _extract_deadline(self, row: Any) -> datetime | None:
        """Deadline is the first '.cloture-line' block (a hidden duplicate may also exist).

        The block shows the date and time on two lines split by a <br>, so its
        strings are joined with a space to keep them apart.
        """
        cloture_div = row.find("div", class_="cloture-line")
        if cloture_div is None:
            return None
        text = cloture_div.get_text(" ", strip=True)
        return parse_deadline(text) if text else None

    def _extract_attr_by_id_suffix(self, soup: BeautifulSoup, id_pattern: str, attr: str) -> str | None:
        """Find an element whose id matches the given (regex) suffix and return an attribute value."""
        node = soup.find(id=re.compile(id_pattern))
        if node is None:
            return None
        value = node.get(attr)
        return value if value else None

    def _extract_text_by_id_suffix(self, soup: BeautifulSoup, id_pattern: str) -> str | None:
        """Find an element whose id matches the given (regex) suffix and return its cleaned text."""
        node = soup.find(id=re.compile(id_pattern))
        return self._clean_text(node) if node is not None else None

    def _to_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _clean_text(self, node: Any) -> str | None:
        text = "".join(node.stripped_strings) if hasattr(node, "stripped_strings") else str(node)
        return re.sub(r"\s+", " ", text).strip() or None