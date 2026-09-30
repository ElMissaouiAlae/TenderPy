"""Discovery client for executing searches against the procurement site."""

from __future__ import annotations

from core.exceptions import HttpRequestError, PaginationError, SearchExecutionError
from core.session import SearchSession

from .parser import SearchCriteria, SearchResultPage, SearchResultParser
from .paginator import Paginator


class DiscoveryClient:
    """Execute searches through a SearchSession and delegate parsing to SearchResultParser."""

    PAGER_BOTTOM_PREFIX = "ctl0$CONTENU_PAGE$resultSearch$PagerBottom"

    PAGER_FIRST = f"{PAGER_BOTTOM_PREFIX}$ctl0"
    PAGER_PREVIOUS = f"{PAGER_BOTTOM_PREFIX}$ctl1"
    PAGER_NEXT = f"{PAGER_BOTTOM_PREFIX}$ctl2"
    PAGER_LAST = f"{PAGER_BOTTOM_PREFIX}$ctl3"

    ROW_ECHO_PREFIX = "ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch"

    SEARCH_URL = "index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
    _POSTBACK_TARGET_PARAM = "PRADO_POSTBACK_TARGET"

    # --- dynamic / user-overridable field names ---
    KEYWORD_PARAM = "ctl0$CONTENU_PAGE$AdvancedSearch$keywordSearch"
    BUYER_PARAM = "ctl0$CONTENU_PAGE$AdvancedSearch$orgName"
    ORGANIZATION_PARAM = "ctl0$CONTENU_PAGE$AdvancedSearch$organismesNames"
    DATE_FROM_PARAM = "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeStart"
    DATE_TO_PARAM = "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeEnd"

    # --- static baseline: fields PRADO expects on every postback, ---
    # --- regardless of what the user searched for ---
    _DEFAULT_PAYLOAD: dict[str, str] = {
        "PRADO_POSTBACK_TARGET": "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche",
        "ctl0$menuGaucheEntreprise$quickSearch": "Recherche rapide",
        "ctl0$CONTENU_PAGE$AdvancedSearch$type_rechercheEntite": "floue",
        "ctl0$CONTENU_PAGE$AdvancedSearch$classification": "0",
        "ctl0$CONTENU_PAGE$AdvancedSearch$organismesNames": "0",
        "ctl0$CONTENU_PAGE$AdvancedSearch$choixInclusionDescendancesServices": (
            "ctl0$CONTENU_PAGE$AdvancedSearch$inclureDescendances"
        ),
        "ctl0$CONTENU_PAGE$AdvancedSearch$procedureType": "0",
        "ctl0$CONTENU_PAGE$AdvancedSearch$categorie": "0",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$modeRecherche": "1",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$typeData": "montant",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idAtexoLtRefRadio$RepeaterReferentielRadio$ctl0$ClientIdsRadio": (
            "ctl0_CONTENU_PAGE_AdvancedSearch_idAtexoLtRefRadio_RepeaterReferentielRadio_ctl0_OptionOui"
            "#ctl0_CONTENU_PAGE_AdvancedSearch_idAtexoLtRefRadio_RepeaterReferentielRadio_ctl0_OptionNon"
        ),
        "ctl0$CONTENU_PAGE$AdvancedSearch$idAtexoLtRefRadio$RepeaterReferentielRadio$ctl0$modeRecherche": "1",
        "ctl0$CONTENU_PAGE$AdvancedSearch$considerationsEnvironnementales": (
            "ctl0$CONTENU_PAGE$AdvancedSearch$considerationsEnvIndifferent"
        ),
        "ctl0$CONTENU_PAGE$AdvancedSearch$rechercheFloue": (
            "ctl0$CONTENU_PAGE$AdvancedSearch$floue"
        ),
        # empty-string defaults included explicitly for clarity / documentation,
        # harmless to omit since dict.get would return None -> not sent anyway,
        # but PRADO seems tolerant of these being absent (unlike the ones above)
    }

    def __init__(self, session: SearchSession) -> None:
        """Initialize the discovery client with an active SearchSession."""
        self._session = session
        self._parser = SearchResultParser()
        self._paginator = Paginator()
        self._last_row_echo: dict[str, str] = {}

    def search(self, criteria: SearchCriteria) -> SearchResultPage:
        """Execute a search and return the first page of results."""
        try:
            payload = self._build_search_payload(criteria)
            payload.update(self._session.state.to_payload())

            response = self._session.post(self.SEARCH_URL, data=payload)

            page = self._parser.parse(response.text)
            self._paginator.sync_from_page(page)
            self._last_row_echo = self._build_row_echo_payload(page)

            return page
        except HttpRequestError as exc:
            raise SearchExecutionError(f"Search request failed: {exc}") from exc
        except Exception as exc:
            raise SearchExecutionError(f"Search execution failed: {exc}") from exc

    def next_page(self, page: SearchResultPage) -> SearchResultPage:
        """Fetch the next page of results."""
        if not self._paginator.has_next_page():
            raise PaginationError("No more pages available")

        try:
            payload = self._paginator.next_page_payload()   # numPage/listePageSize, Top+Bottom
            payload.update(self._last_row_echo)              # from previously parsed page
            payload[self._POSTBACK_TARGET_PARAM] = self.PAGER_NEXT   # always this, never computed
            payload.update(self._session.state.to_payload())  # freshest pagestate wins

            response = self._session.post(self.SEARCH_URL, data=payload)
            page = self._parser.parse(response.text)

            self._paginator.sync_from_page(page)
            self._last_row_echo = self._build_row_echo_payload(page)  # refresh for page N+2

            return page
        except PaginationError:
            raise
        except HttpRequestError as exc:
            raise SearchExecutionError(f"Pagination request failed: {exc}") from exc
        except Exception as exc:
            raise SearchExecutionError(f"Pagination failed: {exc}") from exc

    def search_all(self, criteria: SearchCriteria) -> list[SearchResultPage]:
        """Execute a search and return all pages of results."""
        all_pages = []
        current_page = self.search(criteria)
        all_pages.append(current_page)

        while self._paginator.has_next_page():
            current_page = self.next_page(current_page)
            all_pages.append(current_page)

        return all_pages

    def _build_search_payload(self, criteria: SearchCriteria) -> dict[str, str]:
        """Convert SearchCriteria into PRADO POST parameters.

        Merge order matters:
          1. Static PRADO defaults (always required baseline)
          2. User-specified criteria (overrides where applicable)
          3. Fresh PRADO state (pagestate etc. — must win, always freshest)
        """
        payload: dict[str, str] = dict(self._DEFAULT_PAYLOAD)

        if criteria.keyword:
            payload[self.KEYWORD_PARAM] = criteria.keyword

        if criteria.buyer:
            payload[self.BUYER_PARAM] = criteria.buyer

        if criteria.organization:
            payload[self.ORGANIZATION_PARAM] = criteria.organization

        if criteria.publication_date_from:
            payload[self.DATE_FROM_PARAM] = criteria.publication_date_from.strftime("%d/%m/%Y")

        if criteria.publication_date_to:
            payload[self.DATE_TO_PARAM] = criteria.publication_date_to.strftime("%d/%m/%Y")

        return payload

    def _build_row_echo_payload(self, page: SearchResultPage) -> dict[str, str]:
        """Reconstruct the ctl{n}$refCons / ctl{n}$orgCons hidden fields
        PRADO expects on the next postback, from already-parsed results.

        Index is 1-based and follows render order — must match exactly
        how PRADO numbered the repeater on the page we parsed. Rows missing
        their identity fields are skipped rather than echoed as the literal
        string "None" (which is what str()-ing a None into form data would send).
        """
        payload: dict[str, str] = {}
        for i, result in enumerate(page.tenders, start=1):
            if result.tender_id is None or result.organization_acronym is None:
                continue
            payload[f"{self.ROW_ECHO_PREFIX}$ctl{i}$refCons"] = result.tender_id
            payload[f"{self.ROW_ECHO_PREFIX}$ctl{i}$orgCons"] = result.organization_acronym
        return payload