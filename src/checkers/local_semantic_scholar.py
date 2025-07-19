#!/usr/bin/env python3
"""
Local Semantic Scholar Database Client for Reference Verification

This module provides functionality to verify non-arXiv references using a local Semantic Scholar database.
It can check if a reference's metadata (authors, year, title) matches what's in the local database.

Usage:
    from local_semantic_scholar import LocalNonArxivReferenceChecker
    
    # Initialize the checker
    checker = LocalNonArxivReferenceChecker(db_path="semantic_scholar_db/semantic_scholar.db")
    
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

import json
import logging
import re
import sqlite3
import time
from typing import Dict, List, Tuple, Optional, Any, Union

# Import utility functions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.doi_utils import extract_doi_from_url, compare_dois, construct_doi_url
from utils.error_utils import create_author_error, create_year_warning, create_doi_error
from utils.text_utils import normalize_author_name, normalize_paper_title, is_name_match, compare_authors
from utils.db_utils import process_semantic_scholar_result, process_semantic_scholar_results
from utils.url_utils import get_best_available_url

# Set up logging
logger = logging.getLogger(__name__)

def log_query_debug(query: str, params: list, execution_time: float, result_count: int, strategy: str):
    """Log database query details in debug mode"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"DB Query Strategy: {strategy}")
        logger.debug(f"DB Query: {query}")
        logger.debug(f"DB Params: {params}")
        logger.debug(f"DB Execution Time: {execution_time:.3f}s")
        logger.debug(f"DB Result Count: {result_count}")
    else:
        # Always log strategy and result count for INFO level
        logger.info(f"DB Query [{strategy}]: {result_count} results in {execution_time:.3f}s")

class LocalNonArxivReferenceChecker:
    """
    A class to verify non-arXiv references using a local Semantic Scholar database
    """
    
    def __init__(self, db_path: str = "semantic_scholar_db/semantic_scholar.db"):
        """
        Initialize the local Semantic Scholar database client
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    
    # DOI extraction now handled by utility function
    
    # Title normalization now handled by utility function
    
    # Author name normalization now handled by utility function
    
    # Author comparison now handled by utility function
    
    # Name matching now handled by utility function
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get paper data by DOI from the local database
        
        Args:
            doi: DOI of the paper
            
        Returns:
            Paper data dictionary or None if not found
        """
        cursor = self.conn.cursor()
        
        # Query the database for the paper with the given DOI using the column-based schema
        query = '''
        SELECT * FROM papers
        WHERE externalIds_DOI = ?
        '''
        params = (doi,)
        
        start_time = time.time()
        cursor.execute(query, params)
        row = cursor.fetchone()
        execution_time = time.time() - start_time
        
        result_count = 1 if row else 0
        log_query_debug(query, list(params), execution_time, result_count, "DOI lookup")
        
        if not row:
            return None
        
        # Convert row to dictionary and process using utility function
        paper_data = process_semantic_scholar_result(dict(row))
        
        return paper_data
    
    def search_papers_by_title(self, title: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for papers by title in the local database with optimized performance
        
        Args:
            title: Paper title
            year: Publication year (optional)
            
        Returns:
            List of paper data dictionaries
        """
        cursor = self.conn.cursor()
        
        # Clean up the title for searching
        title_cleaned = title.replace('%', '').strip()
        title_lower = title_cleaned.lower()
        title_normalized = normalize_paper_title(title_cleaned)
        
        results = []
        
        # Strategy 1: Try normalized title match first (fastest and most accurate)
        try:
            cursor.execute("PRAGMA table_info(papers)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'normalized_paper_title' in columns and title_normalized:
                query = "SELECT * FROM papers WHERE normalized_paper_title = ?"
                params = [title_normalized]
                    
                start_time = time.time()
                cursor.execute(query, params)
                results.extend([dict(row) for row in cursor.fetchall()])
                execution_time = time.time() - start_time
                
                log_query_debug(query, params, execution_time, len(results), "normalized title match")
                
                if results:
                    logger.debug(f"Found {len(results)} results using normalized title match")
                    return process_semantic_scholar_results(results)
        except Exception as e:
            logger.warning(f"Error in normalized title search: {e}")
        
        return process_semantic_scholar_results(results)
    
    # Result processing now handled by utility function
    
    def search_papers_by_author(self, author_name: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for papers by author name in the local database
        
        Args:
            author_name: Author name
            year: Publication year (optional)
            
        Returns:
            List of paper data dictionaries
        """
        cursor = self.conn.cursor()
        
        # Clean up the author name for searching
        search_name = f"%{author_name.replace('%', '').lower()}%"
        
        # Build the query using the column-based schema with JSON_EXTRACT for authors
        query = '''
        SELECT * FROM papers
        WHERE LOWER(authors) LIKE ?
        '''
        params = [search_name]
        
        # Add year filter if provided
        if year:
            query += ' AND year = ?'
            params.append(year)
        
        # Execute the query
        start_time = time.time()
        cursor.execute(query, params)
        execution_time = time.time() - start_time
        
        # Fetch results
        results = []
        raw_results = cursor.fetchall()
        
        log_query_debug(query, params, execution_time, len(raw_results), "author name search")
        
        for row in raw_results:
            # Convert row to dictionary and reconstruct paper data structure
            paper_data = dict(row)
            
            # Extract authors from JSON
            if paper_data.get('authors'):
                authors_list = json.loads(paper_data['authors'])
                paper_data['authors'] = authors_list
                
                # Check if any author actually matches our search
                author_match = False
                for author in authors_list:
                    author_name_normalized = normalize_author_name(author.get('name', ''))
                    search_name_normalized = normalize_author_name(author_name)
                    if search_name_normalized in author_name_normalized:
                        author_match = True
                        break
                
                # Skip if no actual author match (reduces false positives)
                if not author_match:
                    continue
            else:
                paper_data['authors'] = []
            
            # Reconstruct external IDs from flattened columns
            external_ids = {}
            for key, value in paper_data.items():
                if key.startswith('externalIds_') and value:
                    external_id_type = key.replace('externalIds_', '')
                    external_ids[external_id_type] = value
            paper_data['externalIds'] = external_ids
            
            # Add other JSON fields
            if paper_data.get('s2FieldsOfStudy'):
                paper_data['s2FieldsOfStudy'] = json.loads(paper_data['s2FieldsOfStudy'])
            if paper_data.get('publicationTypes'):
                paper_data['publicationTypes'] = json.loads(paper_data['publicationTypes'])
            
            results.append(paper_data)
        
        return results
    
    def find_best_match(self, title: str, authors: List[str], year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Find the best matching paper in the local database
        
        Args:
            title: Paper title
            authors: List of author names
            year: Publication year (optional)
            
        Returns:
            Best matching paper data dictionary or None if not found
        """
        logger.debug(f"Local DB: Finding best match for title: '{title}', authors: {authors}, year: {year}")
        
        # Search by title
        title_results = self.search_papers_by_title(title, year)
        
        logger.debug(f"Local DB: Title search returned {len(title_results)} results")
        
        if title_results:
            # Find the best match by title similarity
            best_match = None
            best_score = 0
            
            for result in title_results:
                result_title = result.get('title', '').lower()
                title_lower = title.lower()
                
                # Calculate a simple similarity score
                if title_lower in result_title or result_title in title_lower:
                    # If one is a substring of the other, it's a good match
                    score = 0.8
                else:
                    # Calculate word overlap
                    title_words = set(title_lower.split())
                    result_words = set(result_title.split())
                    common_words = title_words.intersection(result_words)
                    
                    if not title_words or not result_words:
                        score = 0
                    else:
                        score = len(common_words) / max(len(title_words), len(result_words))
                
                # Check author match
                if authors and result.get('authors'):
                    # Compare first author
                    first_author = normalize_author_name(authors[0])
                    result_first_author = normalize_author_name(result['authors'][0].get('name', ''))
                    
                    if is_name_match(first_author, result_first_author):
                        score += 0.2
                
                # Check year match
                if year and result.get('year') == year:
                    score += 0.1
                
                logger.debug(f"Local DB: Candidate match score {score:.2f} for '{result_title}'")
                
                if score > best_score:
                    best_score = score
                    best_match = result
            
            # If we found a good match, return it
            if best_score >= 0.7:
                logger.debug(f"Local DB: Found good title match with score {best_score:.2f}")
                return best_match
            else:
                logger.debug(f"Local DB: Best title match score {best_score:.2f} below threshold (0.7)")
        
        logger.debug("Local DB: No good match found")
        return None
    
    def verify_reference(self, reference: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Verify a non-arXiv reference using the local database
        
        Args:
            reference: Reference data dictionary
            
        Returns:
            Tuple of (verified_data, errors, url)
            - verified_data: Paper data from the database or None if not found
            - errors: List of error dictionaries
            - url: URL of the paper if found, None otherwise
        """
        errors = []
        
        # Extract reference data
        title = reference.get('title', '')
        authors = reference.get('authors', [])
        year = reference.get('year', 0)
        url = reference.get('url', '')
        raw_text = reference.get('raw_text', '')
        
        logger.debug(f"Local DB: Verifying reference - Title: '{title}', Authors: {authors}, Year: {year}")
        
        # If we have a DOI, try to get the paper directly
        doi = None
        if 'doi' in reference and reference['doi']:
            doi = reference['doi']
        elif url:
            doi = extract_doi_from_url(url)
        
        paper_data = None
        
        if doi:
            logger.debug(f"Local DB: Searching by DOI: {doi}")
            # Try to get the paper by DOI
            paper_data = self.get_paper_by_doi(doi)
            
            if paper_data:
                logger.info(f"Found paper by DOI: {doi}")
            else:
                logger.warning(f"Could not find paper with DOI: {doi}")
        
        # If we couldn't get the paper by DOI, try searching by title and authors
        if not paper_data and (title or authors):
            logger.debug(f"Local DB: Searching by title/authors - Title: '{title}', Authors: {authors}, Year: {year}")
            paper_data = self.find_best_match(title, authors, year)
            
            if paper_data:
                logger.debug(f"Found paper by title/author search")
            else:
                logger.debug(f"Could not find matching paper for reference")
        
        # If we couldn't find the paper, return no errors (can't verify)
        if not paper_data:
            logger.debug("Local DB: No matching paper found - cannot verify reference")
            return None, [], None
        
        logger.debug(f"Local DB: Found matching paper - Title: '{paper_data.get('title', '')}', Year: {paper_data.get('year', '')}")
        
        # Verify authors
        if authors:
            authors_match, author_error = compare_authors(authors, paper_data.get('authors', []))
            
            if not authors_match:
                logger.debug(f"Local DB: Author mismatch - {author_error}")
                errors.append(create_author_error(author_error, paper_data.get('authors', [])))
        
        # Verify year
        paper_year = paper_data.get('year')
        if year and paper_year and year != paper_year:
            logger.debug(f"Local DB: Year mismatch - cited: {year}, actual: {paper_year}")
            errors.append(create_year_warning(year, paper_year))
        
        # Verify DOI
        paper_doi = None
        external_ids = paper_data.get('externalIds', {})
        if external_ids and 'DOI' in external_ids:
            paper_doi = external_ids['DOI']
            
            # Compare DOIs using utility function
            if doi and paper_doi and not compare_dois(doi, paper_doi):
                logger.debug(f"Local DB: DOI mismatch - cited: {doi}, actual: {paper_doi}")
                errors.append(create_doi_error(doi, paper_doi))
        
        if errors:
            logger.debug(f"Local DB: Found {len(errors)} errors in reference verification")
        else:
            logger.debug("Local DB: Reference verification passed - no errors found")
        
        # Extract URL using utility function
        external_ids = paper_data.get('externalIds', {})
        open_access_pdf = paper_data.get('openAccessPdf')
        paper_url = get_best_available_url(external_ids, open_access_pdf)
        
        if paper_url:
            logger.debug(f"Found best available URL: {paper_url}")
        
        return paper_data, errors, paper_url
    
    def close(self):
        """Close the database connection"""
        self.conn.close()

if __name__ == "__main__":
    # Example usage
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Check if database path is provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "semantic_scholar_db/semantic_scholar.db"
    
    # Initialize the checker
    checker = LocalNonArxivReferenceChecker(db_path=db_path)
    
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
    
    # Close the database connection
    checker.close()
