#!/usr/bin/env python3
"""
Semantic Scholar API Client for Reference Verification

This module provides functionality to verify non-arXiv references using the Semantic Scholar API.
It can check if a reference's metadata (authors, year, title) matches what's in the Semantic Scholar database.

Usage:
    from semantic_scholar import NonArxivReferenceChecker
    
    # Initialize the checker
    checker = NonArxivReferenceChecker(api_key="your_api_key")  # API key is optional
    
    # Verify a reference
    reference = {
        'title': 'Title of the paper',
        'authors': ['Author 1', 'Author 2'],
        'year': 2020,
        'url': 'https://example.com/paper',
        'raw_text': 'Full citation text'
    }
    
    verified_data, errors = checker.verify_reference(reference)
"""

import requests
import time
import logging
import re
from typing import Dict, List, Tuple, Optional, Any, Union
from utils.text_utils import normalize_text, clean_title_basic, find_best_match, is_name_match, are_venues_substantially_different, calculate_title_similarity, compare_authors, clean_title_for_search
from config.settings import get_config

# Set up logging
logger = logging.getLogger(__name__)

# Get configuration
config = get_config()
SIMILARITY_THRESHOLD = config["text_processing"]["similarity_threshold"]

class NonArxivReferenceChecker:
    """
    A class to verify non-arXiv references using the Semantic Scholar API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Semantic Scholar API client
        
        Args:
            api_key: Optional API key for Semantic Scholar (increases rate limits)
        """
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "Accept": "application/json"
        }
        
        if api_key:
            self.headers["x-api-key"] = api_key
        
        # Rate limiting parameters
        self.request_delay = 1.0  # Initial delay between requests (seconds)
        self.max_retries = 5  # Sufficient for individual API calls
        self.backoff_factor = 2  # Exponential backoff factor
        
        # Track API failures for Enhanced Hybrid Checker
        self._api_failed = False
        self._failure_reason = None
    
    def search_paper(self, query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for papers matching the query
        
        Args:
            query: Search query (title, authors, etc.)
            year: Publication year to filter by
            
        Returns:
            List of paper data dictionaries
        """
        endpoint = f"{self.base_url}/paper/search"
        
        # Build query parameters
        params = {
            "query": query,
            "limit": 10,
            "fields": "title,authors,year,externalIds,url,abstract,openAccessPdf,isOpenAccess,venue,journal",
            "sort": "relevance"  # Ensure consistent ordering
        }
        
        # Make the request with retries and backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                # Check for rate limiting
                if response.status_code == 429:
                    wait_time = self.request_delay * (self.backoff_factor ** attempt)
                    logger.debug(f"Rate limit exceeded. Increasing delay and retrying...")
                    time.sleep(wait_time)
                    continue
                
                # Check for other errors
                response.raise_for_status()
                
                # Parse the response
                data = response.json()
                return data.get('data', [])
                
            except requests.exceptions.RequestException as e:
                wait_time = self.request_delay * (self.backoff_factor ** attempt)
                logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        # If we get here, all retries failed
        logger.debug(f"Failed to search for paper after {self.max_retries} attempts")
        self._api_failed = True
        self._failure_reason = "rate_limited_or_timeout"
        return []
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get paper data by DOI
        
        Args:
            doi: DOI of the paper
            
        Returns:
            Paper data dictionary or None if not found
        """
        endpoint = f"{self.base_url}/paper/DOI:{doi}"
        
        params = {
            "fields": "title,authors,year,externalIds,url,abstract,openAccessPdf,isOpenAccess,venue,journal"
        }
        
        # Make the request with retries and backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                
                # Check for rate limiting
                if response.status_code == 429:
                    wait_time = self.request_delay * (self.backoff_factor ** attempt)
                    logger.debug(f"Rate limit exceeded. Increasing delay and retrying...")
                    time.sleep(wait_time)
                    continue
                
                # If not found, return None
                if response.status_code == 404:
                    logger.debug(f"Paper with DOI {doi} not found")
                    return None
                
                # Check for other errors
                response.raise_for_status()
                
                # Parse the response
                return response.json()
                
            except requests.exceptions.RequestException as e:
                wait_time = self.request_delay * (self.backoff_factor ** attempt)
                logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        # If we get here, all retries failed
        logger.error(f"Failed to get paper by DOI after {self.max_retries} attempts")
        self._api_failed = True
        self._failure_reason = "rate_limited_or_timeout"
        return None
    
    def extract_doi_from_url(self, url: str) -> Optional[str]:
        """
        Extract DOI from a URL
        
        Args:
            url: URL that might contain a DOI
            
        Returns:
            Extracted DOI or None if not found
        """
        if not url:
            return None
        
        # Check if it's a DOI URL
        if 'doi.org' in url:
            # Extract the DOI part after doi.org/
            match = re.search(r'doi\.org/([^/\s]+)', url)
            if match:
                return match.group(1)
        
        return None
    
    def normalize_author_name(self, name: str) -> str:
        """
        Normalize author name for comparison
        
        Args:
            name: Author name
            
        Returns:
            Normalized name
        """
        # Remove reference numbers (e.g., "[1]")
        name = re.sub(r'^\[\d+\]', '', name)
        
        # Use common normalization function
        return normalize_text(name)
    
    def compare_authors(self, cited_authors: List[str], correct_authors: List[Dict[str, str]]) -> Tuple[bool, str]:
        """
        Compare author lists to check if they match (delegates to shared utility)
        
        Args:
            cited_authors: List of author names as cited
            correct_authors: List of author data from Semantic Scholar
            
        Returns:
            Tuple of (match_result, error_message)
        """
        return compare_authors(cited_authors, correct_authors)
    
    
    
    def verify_reference(self, reference: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Verify a non-arXiv reference using Semantic Scholar
        
        Args:
            reference: Reference data dictionary
            
        Returns:
            Tuple of (verified_data, errors, url)
            - verified_data: Paper data from Semantic Scholar or None if not found
            - errors: List of error dictionaries
            - url: URL of the paper if found, None otherwise
        """
        # Reset API failure tracking for this verification attempt
        self._api_failed = False
        self._failure_reason = None
        
        errors = []
        
        # Extract reference data
        title = reference.get('title', '')
        authors = reference.get('authors', [])
        year = reference.get('year', 0)
        url = reference.get('url', '')
        raw_text = reference.get('raw_text', '')
        
        # If we have a DOI, try to get the paper directly
        doi = None
        if 'doi' in reference and reference['doi']:
            doi = reference['doi']
        elif url:
            doi = self.extract_doi_from_url(url)
        
        paper_data = None
        
        if doi:
            # Try to get the paper by DOI
            paper_data = self.get_paper_by_doi(doi)
            
            if paper_data:
                logger.debug(f"Found paper by DOI: {doi}")
            else:
                logger.warning(f"Could not find paper with DOI: {doi}")
        
        # If we couldn't get the paper by DOI, try searching by title
        found_title = ''
        if not paper_data and title:
            # Clean up the title for search using centralized utility function
            cleaned_title = clean_title_for_search(title)
            
            # Search for the paper using cleaned query
            search_results = self.search_paper(cleaned_title, year)
            
            if search_results:
                best_match, best_score = find_best_match(search_results, cleaned_title, year, authors)
                
                # Consider it a match if similarity is above threshold
                if best_match and best_score >= SIMILARITY_THRESHOLD:
                    paper_data = best_match
                    found_title = best_match['title']
                    logger.debug(f"Found paper by title with similarity {best_score:.2f}: {cleaned_title}")
                else:
                    logger.debug(f"No good match found for title: {cleaned_title}")
            else:
                logger.debug(f"No papers found for title: {cleaned_title}")
        
        # If we still couldn't find the paper, try searching by ArXiv ID if available
        if not paper_data and url and 'arxiv.org/abs/' in url:
            # Extract ArXiv ID from URL
            arxiv_match = re.search(r'arxiv\.org/abs/([^\s/?#]+)', url)
            if arxiv_match:
                arxiv_id = arxiv_match.group(1)
                logger.debug(f"Trying to find paper by ArXiv ID: {arxiv_id}")
                
                # Search using ArXiv ID
                search_results = self.search_paper(f"arXiv:{arxiv_id}")
                
                if search_results:
                    # For ArXiv searches, be more lenient with matching
                    for result in search_results:
                        external_ids = result.get('externalIds', {})
                        if external_ids and external_ids.get('ArXiv') == arxiv_id:
                            paper_data = result
                            found_title = result['title']
                            logger.debug(f"Found paper by ArXiv ID: {arxiv_id}")
                            break
                
                # If still not found after ArXiv ID search, try ArXiv API directly
                if not paper_data:
                    logger.debug(f"Paper not found in Semantic Scholar by ArXiv ID, trying ArXiv API directly for: {arxiv_id}")
                    arxiv_paper = self._get_paper_from_arxiv_api(arxiv_id)
                    if arxiv_paper:
                        paper_data = arxiv_paper
                        found_title = arxiv_paper['title']
                        logger.debug(f"Found paper in ArXiv API: {arxiv_id}")
        
        # If we still couldn't find the paper, try searching by the raw text
        if not paper_data and raw_text:
            # Extract and normalize a reasonable search query from the raw text
            search_query = raw_text.replace('\n', ' ').strip()
            normalized_raw_query = normalize_text(search_query).lower().strip()
            
            # Search for the paper using normalized query
            search_results = self.search_paper(normalized_raw_query)
            
            if search_results:
                # Take the first result as a best guess
                best_match, best_score = find_best_match(search_results, cleaned_title, year, authors)
                
                # Consider it a match if similarity is above threshold
                if best_match and best_score >= SIMILARITY_THRESHOLD:
                    paper_data = best_match
                    found_title = best_match['title']
                    logger.debug(f"Found paper by raw text search")
                else:
                    logger.debug(f"No good match found for raw text search: {search_query}")
            else:
                logger.debug(f"No papers found for raw text search")
        
        # If we couldn't find the paper, check if API failed or genuinely not found
        if not paper_data:
            logger.debug(f"Could not find matching paper for reference: {title}")
            logger.debug(f"Tried: DOI search, title search, ArXiv ID search, ArXiv API fallback, raw text search")
            
            # If API failed during search, return error indicating retryable failure
            if self._api_failed:
                return None, [{"error_type": "api_failure", "error_details": f"Semantic Scholar API failed: {self._failure_reason}"}], None
            else:
                # Paper genuinely not found in database
                return None, [], None
        
        # Check title using similarity function to handle formatting differences
        title_similarity = calculate_title_similarity(title, found_title) if found_title else 0.0
        if found_title and title_similarity < SIMILARITY_THRESHOLD:
            errors.append({
                'error_type': 'title',
                'error_details': f"Title mismatch: cited as '{title}' but actually '{found_title}'",
                'ref_title_correct': paper_data.get('title', '')
            })
        
        # Verify authors
        if authors:
            authors_match, author_error = self.compare_authors(authors, paper_data.get('authors', []))
            
            if not authors_match:
                # Check if we have an exact ArXiv ID match - if so, be more lenient with author mismatches
                # since they might be due to incomplete data in Semantic Scholar
                arxiv_id_match = False
                if url and 'arxiv.org/abs/' in url:
                    arxiv_match = re.search(r'arxiv\.org/abs/([^\s/?#]+)', url)
                    if arxiv_match:
                        cited_arxiv_id = arxiv_match.group(1)
                        external_ids = paper_data.get('externalIds', {})
                        found_arxiv_id = external_ids.get('ArXiv')
                        arxiv_id_match = (cited_arxiv_id == found_arxiv_id)
                
                # If ArXiv IDs match exactly, treat author mismatch as warning (likely incomplete data)
                if arxiv_id_match:
                    errors.append({
                        'warning_type': 'author',
                        'warning_details': f"{author_error} (Note: ArXiv ID matches exactly - this may be due to incomplete author data in Semantic Scholar)",
                        'ref_authors_correct': ', '.join([author.get('name', '') for author in paper_data.get('authors', [])])
                    })
                else:
                    # No ArXiv ID match, treat as error
                    errors.append({
                        'error_type': 'author',
                        'error_details': author_error,
                        'ref_authors_correct': ', '.join([author.get('name', '') for author in paper_data.get('authors', [])])
                    })
        
        # Verify year
        paper_year = paper_data.get('year')
        if year and paper_year and year != paper_year:
            # Check if we have an exact ArXiv ID match for additional context
            arxiv_id_match = False
            if url and 'arxiv.org/abs/' in url:
                arxiv_match = re.search(r'arxiv\.org/abs/([^\s/?#]+)', url)
                if arxiv_match:
                    cited_arxiv_id = arxiv_match.group(1)
                    external_ids = paper_data.get('externalIds', {})
                    found_arxiv_id = external_ids.get('ArXiv')
                    arxiv_id_match = (cited_arxiv_id == found_arxiv_id)
            
            warning_details = f"Year mismatch: cited as {year} but actually {paper_year}"
            if arxiv_id_match:
                warning_details += " (Note: ArXiv ID matches exactly - this may be due to conference vs. preprint year difference)"
            
            errors.append({
                'warning_type': 'year',
                'warning_details': warning_details,
                'ref_year_correct': paper_year
            })
        
        # Verify venue
        cited_venue = reference.get('journal', '') or reference.get('venue', '')
        paper_venue = paper_data.get('venue') or paper_data.get('journal')
        
        # Ensure paper_venue is a string (sometimes it can be a dict)
        if isinstance(paper_venue, dict):
            paper_venue = paper_venue.get('name', '') if paper_venue else ''
        elif paper_venue and not isinstance(paper_venue, str):
            paper_venue = str(paper_venue)
        
        if cited_venue and paper_venue:
            # Use the utility function to check if venues are substantially different
            if are_venues_substantially_different(cited_venue, paper_venue):
                errors.append({
                    'warning_type': 'venue',
                    'warning_details': f"Venue mismatch: cited as '{cited_venue}' but actually '{paper_venue}'",
                    'ref_venue_correct': paper_venue
                })
        elif not cited_venue and paper_venue:
            # Check if this is an arXiv paper first
            external_ids = paper_data.get('externalIds', {})
            arxiv_id = external_ids.get('ArXiv') if external_ids else None
            
            if arxiv_id:
                # For arXiv papers, suggest including the arXiv URL instead of venue
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                errors.append({
                    'warning_type': 'venue',
                    'warning_details': f"Reference should include arXiv URL: {arxiv_url}",
                    'ref_url_correct': arxiv_url
                })
            else:
                # Original reference has the venue in raw text but not parsed correctly
                raw_text = reference.get('raw_text', '')
                if raw_text and '#' in raw_text:
                    # Check if venue might be in the raw text format (author#title#venue#year#url)
                    parts = raw_text.split('#')
                    if len(parts) >= 3 and parts[2].strip():
                        # Venue is present in raw text but missing from parsed reference
                        errors.append({
                            'warning_type': 'venue',
                            'warning_details': f"Venue missing: should include '{paper_venue}'",
                            'ref_venue_correct': paper_venue
                        })

        # Verify DOI
        paper_doi = None
        external_ids = paper_data.get('externalIds', {})
        if external_ids and 'DOI' in external_ids:
            paper_doi = external_ids['DOI']
            
            # Compare DOIs, but strip hash fragments for comparison
            cited_doi_clean = doi.split('#')[0] if doi else ''
            paper_doi_clean = paper_doi.split('#')[0] if paper_doi else ''
            
            if cited_doi_clean and paper_doi_clean and cited_doi_clean.lower() != paper_doi_clean.lower():
                errors.append({
                    'error_type': 'doi',
                    'error_details': f"DOI mismatch: cited as {doi} but actually {paper_doi}",
                    'ref_doi_correct': paper_doi
                })
        
        # Extract URL from paper data - prioritize arXiv URLs when available
        paper_url = None
        
        logger.debug(f"Semantic Scholar - Extracting URL from paper data: {list(paper_data.keys())}")
        
        # First priority: arXiv URL if available (most canonical for arXiv papers)
        if external_ids.get('ArXiv'):
            arxiv_id = external_ids['ArXiv']
            paper_url = f"https://arxiv.org/abs/{arxiv_id}"
            logger.debug(f"Found arXiv URL: {paper_url}")
        
        # Second priority: open access PDF (most useful for non-arXiv papers)
        if not paper_url:
            open_access_pdf = paper_data.get('openAccessPdf')
            if open_access_pdf and open_access_pdf.get('url'):
                paper_url = open_access_pdf['url']
                logger.debug(f"Found open access PDF URL: {paper_url}")
        
        # Third priority: general URL field (typically Semantic Scholar page)
        if not paper_url:
            paper_url = paper_data.get('url')
            if paper_url:
                logger.debug(f"Found paper URL: {paper_url}")
        
        # Fourth priority: DOI URL
        if not paper_url:
            if external_ids.get('DOI'):
                # Use the utility function to construct consistent DOI URLs
                from utils.doi_utils import construct_doi_url
                paper_url = construct_doi_url(external_ids['DOI'])
                logger.debug(f"Generated DOI URL: {paper_url}")
        
        if not paper_url:
            logger.debug(f"No URL found in paper data - available fields: {list(paper_data.keys())}")
            logger.debug(f"Paper data sample: {str(paper_data)[:200]}...")
        
        return paper_data, errors, paper_url
    
    def _get_paper_from_arxiv_api(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get paper metadata directly from ArXiv API for very recent papers not yet in Semantic Scholar.
        
        Args:
            arxiv_id: ArXiv ID (e.g., "2507.08846")
            
        Returns:
            Paper data dictionary in Semantic Scholar format, or None if not found
        """
        try:
            import xml.etree.ElementTree as ET
            
            arxiv_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
            logger.debug(f"Querying ArXiv API: {arxiv_url}")
            
            response = requests.get(arxiv_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            # Check if any entries were found
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if not entries:
                logger.debug(f"No entries found for ArXiv ID: {arxiv_id}")
                return None
            
            entry = entries[0]  # Take the first entry
            
            # Extract title
            title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
            title = title_elem.text.strip() if title_elem is not None else ""
            
            # Extract authors
            authors = []
            for author_elem in entry.findall('{http://www.w3.org/2005/Atom}author'):
                name_elem = author_elem.find('{http://www.w3.org/2005/Atom}name')
                if name_elem is not None:
                    authors.append({"name": name_elem.text.strip()})
            
            # Extract published date
            published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
            year = None
            if published_elem is not None:
                published_date = published_elem.text
                try:
                    year = int(published_date[:4])
                except (ValueError, IndexError):
                    pass
            
            # Create Semantic Scholar-compatible data structure
            paper_data = {
                'title': title,
                'authors': authors,
                'year': year,
                'externalIds': {'ArXiv': arxiv_id},
                'url': f"https://arxiv.org/abs/{arxiv_id}",
                'venue': 'arXiv',
                'isOpenAccess': True,
                'openAccessPdf': {'url': f"https://arxiv.org/pdf/{arxiv_id}.pdf"}
            }
            
            logger.debug(f"Successfully retrieved ArXiv paper: {title}")
            return paper_data
            
        except Exception as e:
            logger.debug(f"Failed to get paper from ArXiv API: {str(e)}")
            return None

if __name__ == "__main__":
    # Example usage
    checker = NonArxivReferenceChecker()
    
    # Example reference
    reference = {
        'title': 'Attention is All You Need',
        'authors': ['Ashish Vaswani', 'Noam Shazeer'],
        'year': 2017,
        'url': 'https://example.com/paper',
        'raw_text': 'Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. Advances in neural information processing systems, 30.'
    }
    
    # Verify the reference
    verified_data, errors = checker.verify_reference(reference)
    
    if verified_data:
        print(f"Found paper: {verified_data.get('title')}")
        
        if errors:
            print("Errors found:")
            for error in errors:
                print(f"  - {error['error_type']}: {error['error_details']}")
        else:
            print("No errors found")
    else:
        print("Could not find matching paper")
