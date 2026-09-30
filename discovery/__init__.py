"""Discovery layer: search execution, pagination, and result parsing."""

from discovery.client import DiscoveryClient
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.paginator import Paginator
from discovery.parser import SearchCriteria, SearchResultPage, SearchResultParser

__all__ = [
    "DiscoveryClient",
    "DiscoveryOrchestrator",
    "Paginator",
    "SearchCriteria",
    "SearchResultPage",
    "SearchResultParser",
]
