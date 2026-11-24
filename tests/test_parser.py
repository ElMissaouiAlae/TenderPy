from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from bs4 import BeautifulSoup

from core.dates import parse_deadline, parse_publication_date
from core.exceptions import HtmlParsingError
from core.models import Tender
from discovery.parser import SearchCriteria, SearchResultPage, SearchResultParser

# Independent of core.dates.MOROCCO, so the tests pin the timezone themselves.
CASABLANCA = ZoneInfo("Africa/Casablanca")


def test_search_criteria_defaults_to_none():
    criteria = SearchCriteria()

    assert criteria.keyword is None
    assert criteria.buyer is None
    assert criteria.organization is None
    assert criteria.publication_date_from is None
    assert criteria.publication_date_to is None


def test_search_criteria_accepts_date_filters():
    criteria = SearchCriteria(
        keyword="infrastructure",
        buyer="City Hall",
        organization="Public Works",
        publication_date_from=date(2026, 1, 15),
        publication_date_to=date(2026, 1, 30),
    )

    assert criteria.keyword == "infrastructure"
    assert criteria.buyer == "City Hall"
    assert criteria.organization == "Public Works"
    assert criteria.publication_date_from == date(2026, 1, 15)
    assert criteria.publication_date_to == date(2026, 1, 30)


def test_search_criteria_rejects_from_date_after_to_date():
    with pytest.raises(ValueError, match="publication_date_from must be <= publication_date_to"):
        SearchCriteria(
            publication_date_from=date(2026, 2, 1),
            publication_date_to=date(2026, 1, 31),
        )


def test_tender_creation_with_defaults():
    tender = Tender()
    assert tender.tender_id is None
    assert tender.organization_acronym is None
    assert tender.procurement_type is None
    assert tender.category is None


def test_tender_creation_with_values():
    tender = Tender(
        tender_id="12345",
        organization_acronym="ORG",
        procurement_type="Open",
        category="Works",
        publication_date=date(2026, 1, 15),
        reference_number="REF-001",
        tender_object="Construction work",
        public_buyer="City Council",
        location="Paris",
        deadline=datetime(2026, 1, 30, 11, 0, tzinfo=CASABLANCA),
    )
    assert tender.tender_id == "12345"
    assert tender.organization_acronym == "ORG"
    assert tender.procurement_type == "Open"


def test_search_result_page_creation_with_defaults():
    page = SearchResultPage()
    assert page.tenders == []
    assert page.current_page is None
    assert page.total_pages is None
    assert page.total_results is None


def test_search_result_page_creation_with_values():
    tenders = [Tender(tender_id="1"), Tender(tender_id="2")]
    page = SearchResultPage(
        tenders=tenders,
        current_page=1,
        total_pages=5,
        total_results=100
    )
    assert len(page.tenders) == 2
    assert page.current_page == 1
    assert page.total_pages == 5


def test_search_result_parser_raises_on_empty_html():
    parser = SearchResultParser()
    with pytest.raises(HtmlParsingError, match="Received empty HTML response"):
        parser.parse("")


def test_search_result_parser_handles_no_results_table():
    html = "<html><body><p>No table here</p></body></html>"
    parser = SearchResultParser()
    page = parser.parse(html)
    assert page.tenders == []
    assert page.current_page is None


def test_search_result_parser_extracts_pagination():
    html = """
    <html>
        <body>
            <input name="ctl0$CONTENU_PAGE$resultSearch$numPageTop" type="text" 
            value="3" id="ctl0_CONTENU_PAGE_resultSearch_numPageTop" title="N° de la page"/>
            <span id="ctl0_CONTENU_PAGE_resultSearch_nombrePageTop">51</span>
            <span id="ctl0_CONTENU_PAGE_resultSearch_nombreElement">501</span>
        </body>
    </html>
    """
    parser = SearchResultParser()
    page = parser.parse(html)
    assert page.current_page == 3
    assert page.total_pages == 51
    assert page.total_results == 501


def test_search_result_parser_handles_missing_pagination():
    html = "<html><body><p>No pagination</p></body></html>"
    parser = SearchResultParser()
    page = parser.parse(html)
    assert page.current_page is None
    assert page.total_pages is None
    assert page.total_results is None


RESULTS_TABLE_HTML = """
<html>
    <body>
        <table id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch">
            <thead>
                <tr>
                    <th id="cons_ref">Reference</th>
                    <th id="cons_objet">Objet</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td headers="cons_ref">
                        <span class="ref">REF-001</span>
                        <div>15/01/2026</div>
                    </td>
                    <td headers="cons_objet">Row 1</td>
                </tr>
                <tr>
                    <td headers="cons_ref">
                        <span class="ref">REF-002</span>
                        <div>16/01/2026</div>
                    </td>
                    <td headers="cons_objet">Row 2</td>
                </tr>
                <tr>
                    <td headers="cons_ref">
                        <span class="ref">REF-003</span>
                        <div>17/01/2026</div>
                    </td>
                    <td headers="cons_objet">Row 3</td>
                </tr>
                <tr class="detail-row">
                    <td colspan="2">Hidden tooltip detail, no cons_ref cell</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
"""


def test_extract_rows_returns_only_data_rows_with_cons_ref_cell():
    soup = BeautifulSoup(RESULTS_TABLE_HTML, "html.parser")
    parser = SearchResultParser()

    rows = parser.extract_rows(soup)

    assert len(rows) == 3
    refs = [row.find("span", class_="ref").text for row in rows]
    assert refs == ["REF-001", "REF-002", "REF-003"]
    
    
HTML_TABLE = """
<table summary="R�sultats de la recherche" class="table-results">
                            <caption>Résultats de la recherche
                </caption>
                            <thead>
                                <tr>
                                    <th class="top" colspan="5">
                                        <span class="left">&nbsp;</span>
                                        <span class="right">&nbsp;</span>
                                    </th>
                                </tr>
                                <tr>
                                    <th class="check-col" id="checkAll" abbr="Tous" style="display:none">
                                        <input title="Tous/Aucun" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_selectAll" type="checkbox" onclick="CheckUnCheckAll(this, 'resultSearch_tableauResultSearch', 'annonceSelection');" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$selectAll"/>
                                    </th>
                                    <th class="col-90" id="cons_ref" abbr="Ref">
                                        Procédure
                    <br/>
                                        Catégorie
                    
                    <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl3" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl3" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Catégorie'"/>
                                        <br/>
                                        Publié le
                    
                    <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl5" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl5" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Publié le'"/>
                                    </th>
                                    <th class="col-450" id="cons_intitule" abbr="Intitule">
                                        Référence
                    
                    <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl7" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl7" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Référence'"/>
                                        <div style="display: none;">
                                            |
                      Contexte/Programmme
                      
                      <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl9" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl9" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Contexte/Programmme'"/>
                                        </div>
                                        <br/>
                                        Objet
                    
                    <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl11" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl11" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Objet'"/>
                                        <br/>
                                        Acheteur public
                    
                    <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl13" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl13" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Organisme'"/>
                                    </th>
                                    <th class="col-90" id="cons_lieuExe" style="display:;">
                                        <span style="display:none;">
                                            Type d'annonce
            								
            								<input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl15" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl15" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Type d'annonce'"/>
                                            <br>
                                        </span>
                                        <span>Lots
                    </span>
                                        <br/>
                                        <span>Lieu d'exécution
                    </span>
                                        <div class="info-clauses" style="display:none">
                                            <br/>
                                            <a href="javascript:void(0);" onmouseover="afficheBulle('infoClauses', this)" onmouseout="cacheBulle('infoClauses')" onfocus="afficheBulle('infoClauses', this)" onblur="cacheBulle('infoClauses')" class="info-suite">Clauses soc./env.
                      </a>
                                            <div class="info-bulle" id="infoClauses">
                                                <div>
                                                    <ul>
                                                        <li>-
                              Clauses sociales 
                            </li>
                                                        <li>-
                              Clauses environnementales 
                            </li>
                                                        <li>-
                              Marchés réservés à des emplois ou des ateliers protégés (EA / ESAT, art. 15 du CMP)
                            </li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                        <br/>
                                    </th>
                                    <th class="col-60" id="cons_dateEnd" abbr="Date limite">
                                        <span style="display:block;">
                                            Date limite de remise des plis

        									
            								 <input type="image" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl0$ctl23" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl0_ctl23" src="themes/images/arrow-tri-off.gif" alt="Trier" title="Trier Par 'Date limite de remise des plis'"/>
                                        </span>
                                        <span style="display:none;">Détail
        								</span>
                                    </th>
                                    <th class="actions" id="cons_actions">Actions
                  </th>
                                </tr>
                            </thead>
                            <tr class="">
                                <td class="check-col" headers="checkAll" style="display:none">
                                    <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl1$refCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_refCons" value="1013506"/>
                                    <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl1$orgCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_orgCons" value="g3h"/>
                                    <input title="Sélectionner" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_annonceSelection" type="checkbox" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl1$annonceSelection"/>
                                </td>
                                <td class="col-90" headers="cons_ref">
                                    <div class="line-info-bulle">
                                        AOO
                    <a href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocTypesProc', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocTypesProc')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocTypesProc', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocTypesProc')" class="info-suite">...
                    </a>
                                    </div>
                                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocTypesProc" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                                        <div id="identification_cons_0_type_procedure">Appel d'offres ouvert
                    </div>
                                    </div>
                                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocCategorie">Services
                  </div>
                                    <div>19/08/2026
                  </div>
                                    <a target="_blank"></a>
                                </td>
                                <td class="col-450" headers="cons_intitule">
                                    <div id="identification_cons_0">
                                        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocIntitule" class="objet-line">
                                            <span id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_reference" class="ref">12/SAP/2026</span>
                                            <div style="display: none;">-
                         
                      </div>
                                            <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosIntitule', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosIntitule')" class="info-suite">...</span>
                                        </div>
                                        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocObjet" class="objet-line">
                                            <strong>Objet
                        : </strong>
                                            Etudes techniques et du suivi des travaux de la sécurisation de l’ensemble des accès de l’Institut Royal de Police et la Division de la Police Equestre à Kénitra (en lot unique). 
                      <span style="" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosBullesObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosBullesObjet')" class="info-suite">...</span>
                                            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosBullesObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                                                <div>Etudes techniques et du suivi des travaux de la sécurisation de l’ensemble des accès de l’Institut Royal de Police et la Division de la Police Equestre à Kénitra (en lot unique).
                        </div>
                                            </div>
                                        </div>
                                        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocDenomination" class="objet-line">
                                            <strong>Acheteur public
                        : </strong>
                                            CHEF DE LA SURETE PROVINCIAL DE KENITRA
                    
                                        </div>
                                </td>
                                <td class="col-90" headers="cons_lieuExe" style="display:;">
                                    <div id="identification_cons_0_lieuxExecution">
                                        <span style="display:none;"></span>
                                        <span>
                                            <a href="javascript:popUp('index.php?page=commun.PopUpDetailLots&orgAccronyme=g3h&refConsultation=1013506&lang=','yes')">
                                                <img src="themes/images/picto-details.gif" style="display:none" alt="Détail des lots" title="Détail des lots"/>
                                            </a>
                                            &nbsp;&nbsp;&nbsp;&nbsp;<span>-</span>
                                        </span>
                                        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocLieuxExec" style="display:;">
                                            KENITRA<br/>
                                            <br/>
                                            <div class="bloc-info-bulle">
                                                <a style="display:none" href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl15_infosLieuExecution', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl15_infosLieuExecution')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl15_infosLieuExecution', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl15_infosLieuExecution')" class="info-suite">...
        	</a>
                                                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl15_infosLieuExecution" class="info-bulle">
                                                    <div>KENITRA</div>
                                                </div>
                                            </div>
                                        </div>
                                        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelBlocCodesNuts" headers="cons_codes_nuts" style="display:none;">
                                            <span onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosLieuExecutionLtRef', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosLieuExecutionLtRef')" class="info-suite" title="Info-bulle">
                                                <span style="display:none;">...</span>
                                            </span>
                                            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosLieuExecutionLtRef" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                                                <div></div>
                                            </div>
                                        </div>
                                </td>
                                <td class="col-60" headers="cons_dateEnd" abbr="Date limite">
                                    <div style="display:;">
                                        <div class="cloture-line">
                                            20/10/2026<br>11:00
                    
                                        </div>
                                    </div>
                                    <div style="display:none;">
                                        <div class="cloture-line">
                                            <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosObjet')" class="info-suite">...</span>
                                            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_infosObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                                                <div></div>
                                            </div>
                                            <!-- %#$this->DataItem->getDetailConsultation()% -->
                                        </div>
                                    </div>
                                    <img src="themes/images/reponse-elec-oblig-avec-signature.gif" alt=" Réponse électronique obligatoire pour cette consultation, avec signature électronique requise " class="certificat" title=" Réponse électronique obligatoire pour cette consultation, avec signature électronique requise " style="display:;"/>
                                    <img src="themes/images/logo-mps-small.png" alt="Cette consultation est un Marché Public Simplifié" title="Cette consultation est un Marché Public Simplifié" style="display:none;"/>
                                </td>
                                <td style="display:" class="actions" headers="cons_actions">
                                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_panelAction" class="actions">
                                        <a target="" href="?page=entreprise.EntrepriseDetailConsultation&refConsultation=1013506&orgAcronyme=g3h">
                                            <img src="themes/images/picto-acces-consultation.gif" alt="Accéder à la consultation" title="Accéder à la consultation"/>
                                        </a>
                                        <a href="index.php?page=commun.DiagnosticPoste&callFrom=entreprise" style="display:;">
                                            <img src="themes/images/picto-test-config.gif" alt="Tester la configuration de mon poste" title="Tester la configuration de mon poste"/>
                                        </a>
                                        <!--Debut liens Partager-->
                                        <!--Fin liens Partager-->
                                        <a href="index.php?page=entreprise.EntrepriseHome&goto=%3Fpage%3Dentreprise.EntrepriseAccueilAuthentifie">
                                            <img src="themes/images/picto-ajout-cart.gif" alt="Ajouter au panier" title="Ajouter au panier"/>
                                        </a>
                                </td>
                                <td style="display:none" class="actions col-panier" headers="cons_actions">
                                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl1_ctl29">
                                        <div class="registre-line">
                                            <span class="intitule">
                                                <img src="themes/images/picto-retrait.gif" alt="Retraits" title="Registre des retraits"/>:
                                            </span>
                                            <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1013506&orgAcronyme=g3h&code=&retraits">0
                      </a>
                                        </div>
                                        <div class="registre-line">
                                            <span class="intitule">
                                                <img src="themes/images/picto-questions.gif" alt="Questions" title="Questions"/>:
                                            </span>
                                            <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1013506&orgAcronyme=g3h&code=&questions">0
                      </a>
                                        </div>
                                        <div class="registre-line">
                                            <span class="intitule">
                                                <img src="themes/images/picto-depot.gif" alt="Dépôts" title="Dépôts"/>:
                                            </span>
                                            <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1013506&orgAcronyme=g3h&depots">0
                      </a>
                                        </div>
                                        <div class="registre-line">
                                            <span class="intitule">
                                                <img src="themes/images/picto-msg-echange.gif" alt="Message échangé" title="Message échangé"/>:
                                            </span>
                                            <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1013506&orgAcronyme=g3h&code=&echanges">0
                      </a>
                                        </div>
                                    </div>
                                    <a href="javascript:popUp('index.php?page=entreprise.popUpGestionPanier&refConsultation=MTAxMzUwNg==&orgAcronyme=g3h&action=suppression','yes');">
                                        <img src="themes/images/picto-remove-cart.gif" alt="Supprimer du panier" title="Supprimer du panier"/>
                                    </a>
                                </td>
                    </div>
                    <!--Debut pictos BASE DCE -->
                    <!-- Fin pictos BASE DCE -->
</tr>
<tr class="on">
    <td class="check-col" headers="checkAll" style="display:none">
        <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl2$refCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_refCons" value="1032618"/>
        <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl2$orgCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_orgCons" value="q1s"/>
        <input title="Sélectionner" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_annonceSelection" type="checkbox" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl2$annonceSelection"/>
    </td>
    <td class="col-90" headers="cons_ref">
        <div class="line-info-bulle">
            AOO
                    <a href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocTypesProc', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocTypesProc')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocTypesProc', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocTypesProc')" class="info-suite">...
                    </a>
        </div>
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocTypesProc" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
            <div id="identification_cons_1_type_procedure">Appel d'offres ouvert
                    </div>
        </div>
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocCategorie">Travaux
                  </div>
        <div>19/08/2026
                  </div>
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_logoConsEnv">
            <div class="spacer-mini"></div>
            <a href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocConsEnv', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocConsEnv')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocConsEnv', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocConsEnv')" class="info-suite">
                <img src="ressources/eco.png" width="24" height="24">
            </a>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocConsEnv" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                <div>Comporte des dispositions envrionnementales
                      </div>
            </div>
        </div>
        <a target="_blank"></a>
    </td>
    <td class="col-450" headers="cons_intitule">
        <div id="identification_cons_1">
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocIntitule" class="objet-line">
                <span id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_reference" class="ref">46045903</span>
                <div style="display: none;">-
                         
                      </div>
                <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosIntitule', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosIntitule')" class="info-suite">...</span>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocObjet" class="objet-line">
                <strong>Objet
                        : </strong>
                Travaux du réseau de distribution du Saiss III- 2ème tranche sur 10 000 ha en 8 lots : 
                      <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosBullesObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosBullesObjet')" class="info-suite">...</span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosBullesObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div>Travaux du réseau de distribution du Saiss III- 2ème tranche sur 10 000 ha en 8 lots :
                        </div>
                </div>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocDenomination" class="objet-line">
                <strong>Acheteur public
                        : </strong>
                CHEF DU PROJET PROVISOIR D'AMENAGEMENT HYDROAGRICOLE DE LA PLAINE DE SAISS
                    
            </div>
    </td>
    <td class="col-90" headers="cons_lieuExe" style="display:;">
        <div id="identification_cons_1_lieuxExecution">
            <span style="display:none;"></span>
            <span>
                <a href="javascript:popUp('index.php?page=commun.PopUpDetailLots&orgAccronyme=q1s&refConsultation=1032618&lang=','yes')">
                    <img src="themes/images/picto-details.gif" style="display:" alt="Détail des lots" title="Détail des lots"/>
                </a>
                &nbsp;&nbsp;&nbsp;&nbsp;
            </span>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocLieuxExec" style="display:;">
                MEKNES<br/>
                EL-HAJEB<br/>
                <div class="bloc-info-bulle">
                    <a style="" href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl15_infosLieuExecution', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl15_infosLieuExecution')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl15_infosLieuExecution', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl15_infosLieuExecution')" class="info-suite">...
        	</a>
                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl15_infosLieuExecution" class="info-bulle">
                        <div>MEKNES, EL-HAJEB</div>
                    </div>
                </div>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelBlocCodesNuts" headers="cons_codes_nuts" style="display:none;">
                <span onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosLieuExecutionLtRef', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosLieuExecutionLtRef')" class="info-suite" title="Info-bulle">
                    <span style="display:none;">...</span>
                </span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosLieuExecutionLtRef" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div></div>
                </div>
            </div>
    </td>
    <td class="col-60" headers="cons_dateEnd" abbr="Date limite">
        <div style="display:;">
            <div class="cloture-line">
                07/10/2026<br>14:00
                    
            </div>
        </div>
        <div style="display:none;">
            <div class="cloture-line">
                <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosObjet')" class="info-suite">...</span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_infosObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div></div>
                </div>
                <!-- %#$this->DataItem->getDetailConsultation()% -->
            </div>
        </div>
        <img src="themes/images/reponse-elec-non.gif" alt="Pas de réponse électronique pour cette consultation" class="certificat" title="Pas de réponse électronique pour cette consultation" style="display:;"/>
        <img src="themes/images/logo-mps-small.png" alt="Cette consultation est un Marché Public Simplifié" title="Cette consultation est un Marché Public Simplifié" style="display:none;"/>
    </td>
    <td style="display:" class="actions" headers="cons_actions">
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_panelAction" class="actions">
            <a target="" href="?page=entreprise.EntrepriseDetailConsultation&refConsultation=1032618&orgAcronyme=q1s">
                <img src="themes/images/picto-acces-consultation.gif" alt="Accéder à la consultation" title="Accéder à la consultation"/>
            </a>
            <a href="index.php?page=commun.DiagnosticPoste&callFrom=entreprise" style="display:;">
                <img src="themes/images/picto-test-config.gif" alt="Tester la configuration de mon poste" title="Tester la configuration de mon poste"/>
            </a>
            <!--Debut liens Partager-->
            <!--Fin liens Partager-->
            <a href="index.php?page=entreprise.EntrepriseHome&goto=%3Fpage%3Dentreprise.EntrepriseAccueilAuthentifie">
                <img src="themes/images/picto-ajout-cart.gif" alt="Ajouter au panier" title="Ajouter au panier"/>
            </a>
    </td>
    <td style="display:none" class="actions col-panier" headers="cons_actions">
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl2_ctl29">
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-retrait.gif" alt="Retraits" title="Registre des retraits"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1032618&orgAcronyme=q1s&code=&retraits">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-questions.gif" alt="Questions" title="Questions"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1032618&orgAcronyme=q1s&code=&questions">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-depot.gif" alt="Dépôts" title="Dépôts"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1032618&orgAcronyme=q1s&depots">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-msg-echange.gif" alt="Message échangé" title="Message échangé"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1032618&orgAcronyme=q1s&code=&echanges">0
                      </a>
            </div>
        </div>
        <a href="javascript:popUp('index.php?page=entreprise.popUpGestionPanier&refConsultation=MTAzMjYxOA==&orgAcronyme=q1s&action=suppression','yes');">
            <img src="themes/images/picto-remove-cart.gif" alt="Supprimer du panier" title="Supprimer du panier"/>
        </a>
    </td>
</div>
<!--Debut pictos BASE DCE -->
<!-- Fin pictos BASE DCE -->
</tr>
<tr class="">
    <td class="check-col" headers="checkAll" style="display:none">
        <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl3$refCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_refCons" value="1030723"/>
        <input type="hidden" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl3$orgCons" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_orgCons" value="d0q"/>
        <input title="Sélectionner" id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_annonceSelection" type="checkbox" name="ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl3$annonceSelection"/>
    </td>
    <td class="col-90" headers="cons_ref">
        <div class="line-info-bulle">
            AOO
                    <a href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocTypesProc', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocTypesProc')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocTypesProc', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocTypesProc')" class="info-suite">...
                    </a>
        </div>
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocTypesProc" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
            <div id="identification_cons_2_type_procedure">Appel d'offres ouvert
                    </div>
        </div>
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocCategorie">Travaux
                  </div>
        <div>06/08/2026
                  </div>
        <a target="_blank"></a>
    </td>
    <td class="col-450" headers="cons_intitule">
        <div id="identification_cons_2">
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocIntitule" class="objet-line">
                <span id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_reference" class="ref">04/2026</span>
                <div style="display: none;">-
                         
                      </div>
                <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosIntitule', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosIntitule')" class="info-suite">...</span>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocObjet" class="objet-line">
                <strong>Objet
                        : </strong>
                Travaux de construction des ouvrages d’art  au douar Ain AL Hammame et Centre Bni Frassen à la commune de Bni Frassen, Province de Taza.    
                      <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosBullesObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosBullesObjet')" class="info-suite">...</span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosBullesObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div>Travaux de construction des ouvrages d’art  au douar Ain AL Hammame et Centre Bni Frassen à la commune de Bni Frassen, Province de Taza.   
                        </div>
                </div>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocDenomination" class="objet-line">
                <strong>Acheteur public
                        : </strong>
                Commune rurale de BNI FRASSEN
                    
            </div>
    </td>
    <td class="col-90" headers="cons_lieuExe" style="display:;">
        <div id="identification_cons_2_lieuxExecution">
            <span style="display:none;"></span>
            <span>
                <a href="javascript:popUp('index.php?page=commun.PopUpDetailLots&orgAccronyme=d0q&refConsultation=1030723&lang=','yes')">
                    <img src="themes/images/picto-details.gif" style="display:none" alt="Détail des lots" title="Détail des lots"/>
                </a>
                &nbsp;&nbsp;&nbsp;&nbsp;<span>-</span>
            </span>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocLieuxExec" style="display:;">
                TAZA<br/>
                <br/>
                <div class="bloc-info-bulle">
                    <a style="display:none" href="javascript:void(0);" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl15_infosLieuExecution', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl15_infosLieuExecution')" onfocus="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl15_infosLieuExecution', this)" onblur="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl15_infosLieuExecution')" class="info-suite">...
        	</a>
                    <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl15_infosLieuExecution" class="info-bulle">
                        <div>TAZA</div>
                    </div>
                </div>
            </div>
            <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelBlocCodesNuts" headers="cons_codes_nuts" style="display:none;">
                <span onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosLieuExecutionLtRef', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosLieuExecutionLtRef')" class="info-suite" title="Info-bulle">
                    <span style="display:none;">...</span>
                </span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosLieuExecutionLtRef" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div></div>
                </div>
            </div>
    </td>
    <td class="col-60" headers="cons_dateEnd" abbr="Date limite">
        <div style="display:;">
            <div class="cloture-line">
                07/10/2026<br>11:00
                    
            </div>
        </div>
        <div style="display:none;">
            <div class="cloture-line">
                <span style="display:none" onmouseover="afficheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosObjet', this)" onmouseout="cacheBulle('ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosObjet')" class="info-suite">...</span>
                <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_infosObjet" class="info-bulle" onmouseover="mouseOverBulle();" onmouseout="mouseOutBulle();">
                    <div></div>
                </div>
                <!-- %#$this->DataItem->getDetailConsultation()% -->
            </div>
        </div>
        <img src="themes/images/reponse-elec-oblig-avec-signature.gif" alt=" Réponse électronique obligatoire pour cette consultation, avec signature électronique requise " class="certificat" title=" Réponse électronique obligatoire pour cette consultation, avec signature électronique requise " style="display:;"/>
        <img src="themes/images/logo-mps-small.png" alt="Cette consultation est un Marché Public Simplifié" title="Cette consultation est un Marché Public Simplifié" style="display:none;"/>
    </td>
    <td style="display:" class="actions" headers="cons_actions">
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_panelAction" class="actions">
            <a target="" href="?page=entreprise.EntrepriseDetailConsultation&refConsultation=1030723&orgAcronyme=d0q">
                <img src="themes/images/picto-acces-consultation.gif" alt="Accéder à la consultation" title="Accéder à la consultation"/>
            </a>
            <a href="index.php?page=commun.DiagnosticPoste&callFrom=entreprise" style="display:;">
                <img src="themes/images/picto-test-config.gif" alt="Tester la configuration de mon poste" title="Tester la configuration de mon poste"/>
            </a>
            <!--Debut liens Partager-->
            <!--Fin liens Partager-->
            <a href="index.php?page=entreprise.EntrepriseHome&goto=%3Fpage%3Dentreprise.EntrepriseAccueilAuthentifie">
                <img src="themes/images/picto-ajout-cart.gif" alt="Ajouter au panier" title="Ajouter au panier"/>
            </a>
    </td>
    <td style="display:none" class="actions col-panier" headers="cons_actions">
        <div id="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_ctl3_ctl29">
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-retrait.gif" alt="Retraits" title="Registre des retraits"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1030723&orgAcronyme=d0q&code=&retraits">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-questions.gif" alt="Questions" title="Questions"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1030723&orgAcronyme=d0q&code=&questions">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-depot.gif" alt="Dépôts" title="Dépôts"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1030723&orgAcronyme=d0q&depots">0
                      </a>
            </div>
            <div class="registre-line">
                <span class="intitule">
                    <img src="themes/images/picto-msg-echange.gif" alt="Message échangé" title="Message échangé"/>:
                </span>
                <a href="https://www.marchespublics.gov.ma/?page=entreprise.EntrepriseDetailsConsultation&refConsultation=1030723&orgAcronyme=d0q&code=&echanges">0
                      </a>
            </div>
        </div>
        <a href="javascript:popUp('index.php?page=entreprise.popUpGestionPanier&refConsultation=MTAzMDcyMw==&orgAcronyme=d0q&action=suppression','yes');">
            <img src="themes/images/picto-remove-cart.gif" alt="Supprimer du panier" title="Supprimer du panier"/>
        </a>
    </td>
</div>
"""


def test_extract_rows_returns_all_rows_from_real_page_chunk():
    soup = BeautifulSoup(HTML_TABLE, "html.parser")
    parser = SearchResultParser()

    rows = parser.extract_rows(soup)

    assert len(rows) == 3


def test_parse_extracts_every_tender_from_real_page_chunk():
    parser = SearchResultParser()

    page = parser.parse(HTML_TABLE)

    assert len(page.tenders) == 3
    assert [t.tender_id for t in page.tenders] == ["1013506", "1032618", "1030723"]
    assert [t.reference_number for t in page.tenders] == ["12/SAP/2026", "46045903", "04/2026"]


def test_parse_reads_typed_dates_from_real_page_chunk():
    parser = SearchResultParser()

    page = parser.parse(HTML_TABLE)

    assert [t.publication_date for t in page.tenders] == [
        date(2026, 8, 19),
        date(2026, 8, 19),
        date(2026, 8, 6),
    ]
    assert [t.deadline for t in page.tenders] == [
        datetime(2026, 10, 20, 11, 0, tzinfo=CASABLANCA),
        datetime(2026, 10, 7, 14, 0, tzinfo=CASABLANCA),
        datetime(2026, 10, 7, 11, 0, tzinfo=CASABLANCA),
    ]
    # Morocco is on UTC+1 outside Ramadan.
    assert page.tenders[0].deadline.utcoffset() == timedelta(hours=1)


def _row_html(publication_date: str, deadline: str) -> str:
    """One result row holding just the date cells, as the platform renders them."""
    return f"""
    <table><tr>
        <td headers="cons_ref"><div>{publication_date}</div></td>
        <td headers="cons_dateEnd"><div class="cloture-line">{deadline}</div></td>
    </tr></table>
    """


def test_deadline_without_a_time_closes_at_end_of_day():
    page = SearchResultParser().parse(_row_html("15/01/2026", "30/01/2026"))

    assert page.tenders[0].deadline == datetime(2026, 1, 30, 23, 59, tzinfo=CASABLANCA)


@pytest.mark.parametrize(
    ("publication_date", "deadline"),
    [
        ("15/01/2026", "à préciser"),
        ("15/01/2026", "31/02/2026 10:00"),
        ("15/01/2026", "30/01/2026 25:00"),
    ],
)
def test_unreadable_deadline_is_none_and_logged(publication_date, deadline, caplog):
    page = SearchResultParser().parse(_row_html(publication_date, deadline))

    assert page.tenders[0].deadline is None
    assert page.tenders[0].publication_date == date(2026, 1, 15)
    assert "Unreadable deadline" in caplog.text


def test_unreadable_publication_date_is_none_and_logged(caplog):
    assert parse_publication_date("31/02/2026") is None
    assert "Unreadable publication date" in caplog.text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("20/10/2026 11:00", datetime(2026, 10, 20, 11, 0, tzinfo=CASABLANCA)),
        ("20/10/2026<br>11:00", datetime(2026, 10, 20, 11, 0, tzinfo=CASABLANCA)),
        ("20/10/2026\n  11:00", datetime(2026, 10, 20, 11, 0, tzinfo=CASABLANCA)),
        # Stored before typed dates, with the date and time run together.
        ("20/10/202611:00", datetime(2026, 10, 20, 11, 0, tzinfo=CASABLANCA)),
        ("20/10/2026", datetime(2026, 10, 20, 23, 59, tzinfo=CASABLANCA)),
        (None, None),
        ("", None),
    ],
)
def test_parse_deadline_reads_every_platform_form(text, expected):
    assert parse_deadline(text) == expected


def test_deadline_during_ramadan_uses_moroccos_offset_then():
    # Morocco moves to UTC+0 for Ramadan (mid-February to mid-March 2026).
    assert parse_deadline("01/03/2026 10:00").utcoffset() == timedelta(0)
