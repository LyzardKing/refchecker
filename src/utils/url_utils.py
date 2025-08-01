#!/usr/bin/env python3
"""
URL Utilities for Reference Checking

This module provides utilities for URL construction, validation, and manipulation
related to academic references.
"""

from typing import Optional
from .doi_utils import normalize_doi


def construct_doi_url(doi: str) -> str:
    """
    Construct a proper DOI URL from a DOI string.
    
    Args:
        doi: DOI string
        
    Returns:
        Full DOI URL
    """
    if not doi:
        return ""
    
    # Normalize the DOI first
    normalized_doi = normalize_doi(doi)
    
    # Construct URL
    return f"https://doi.org/{normalized_doi}"


def construct_arxiv_url(arxiv_id: str, url_type: str = "abs") -> str:
    """
    Construct an ArXiv URL from an ArXiv ID.
    
    Args:
        arxiv_id: ArXiv identifier
        url_type: Type of URL ('abs' for abstract, 'pdf' for PDF)
        
    Returns:
        Full ArXiv URL
    """
    if not arxiv_id:
        return ""
    
    # Remove version number if present for consistency
    clean_id = arxiv_id.replace('v1', '').replace('v2', '').replace('v3', '')
    
    if url_type == "pdf":
        return f"https://arxiv.org/pdf/{clean_id}.pdf"
    else:
        return f"https://arxiv.org/abs/{clean_id}"


def construct_semantic_scholar_url(paper_id: str) -> str:
    """
    Construct a Semantic Scholar URL from a paper ID.
    
    Args:
        paper_id: Semantic Scholar paper ID
        
    Returns:
        Full Semantic Scholar URL
    """
    if not paper_id:
        return ""
    
    return f"https://www.semanticscholar.org/paper/{paper_id}"


def construct_openalex_url(work_id: str) -> str:
    """
    Construct an OpenAlex URL from a work ID.
    
    Args:
        work_id: OpenAlex work identifier
        
    Returns:
        Full OpenAlex URL
    """
    if not work_id:
        return ""
    
    # Remove prefix if present
    clean_id = work_id.replace('https://openalex.org/', '')
    
    return f"https://openalex.org/{clean_id}"


def construct_pubmed_url(pmid: str) -> str:
    """
    Construct a PubMed URL from a PMID.
    
    Args:
        pmid: PubMed identifier
        
    Returns:
        Full PubMed URL
    """
    if not pmid:
        return ""
    
    # Remove PMID prefix if present
    clean_pmid = pmid.replace('PMID:', '').strip()
    
    return f"https://pubmed.ncbi.nlm.nih.gov/{clean_pmid}/"


def get_best_available_url(external_ids: dict, open_access_pdf: Optional[str] = None) -> Optional[str]:
    """
    Get the best available URL from a paper's external IDs and open access information.
    Priority: Open Access PDF > DOI > ArXiv > Semantic Scholar > OpenAlex > PubMed
    
    Args:
        external_ids: Dictionary of external identifiers
        open_access_pdf: Open access PDF URL if available
        
    Returns:
        Best available URL or None if no valid URL found
    """
    # Priority 1: Open access PDF
    if open_access_pdf:
        return open_access_pdf
    
    # Priority 2: DOI URL
    if external_ids.get('DOI'):
        return construct_doi_url(external_ids['DOI'])
    
    # Priority 3: ArXiv URL
    if external_ids.get('ArXiv'):
        return construct_arxiv_url(external_ids['ArXiv'])
    
    # Priority 4: Semantic Scholar URL
    if external_ids.get('CorpusId'):
        return construct_semantic_scholar_url(external_ids['CorpusId'])
    
    # Priority 5: OpenAlex URL
    if external_ids.get('OpenAlex'):
        return construct_openalex_url(external_ids['OpenAlex'])
    
    # Priority 6: PubMed URL
    if external_ids.get('PubMed'):
        return construct_pubmed_url(external_ids['PubMed'])
    
    return None


def validate_url_format(url: str) -> bool:
    """
    Basic validation of URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears to be valid, False otherwise
    """
    if not url:
        return False
    
    # Basic URL format check
    return url.startswith(('http://', 'https://')) and '.' in url


def clean_url(url: str) -> str:
    """
    Clean a URL by removing common issues like extra spaces, fragments, etc.
    
    Args:
        url: URL to clean
        
    Returns:
        Cleaned URL
    """
    if not url:
        return ""
    
    # Remove leading/trailing whitespace
    url = url.strip()
    
    # Remove common tracking parameters
    if '?' in url:
        base_url, params = url.split('?', 1)
        # Keep only essential parameters (like DOI redirects)
        if 'doi.org' in base_url:
            return base_url
        # For other URLs, might want to preserve specific params
        url = base_url
    
    return url