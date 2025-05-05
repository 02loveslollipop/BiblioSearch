import requests
import threading
from typing import Dict, Any, Union
from requests.exceptions import HTTPError
from models import ScopusSearchEquation
import logging
import os

class ScopusAPI:
    """
    Singleton controller for making requests to the Scopus Search API.
    """
    _instance = None
    _lock = threading.Lock()
    BASE_URL = "https://api.elsevier.com/content/search/scopus"
    
    def __new__(cls, api_key: str, *args, **kwargs) -> "ScopusAPI":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.api_key = api_key
                
                # Initialize logger configuration when creating the singleton
                log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scopus_api.log')
                
                # Configure logger
                cls._instance.logger = logging.getLogger('ScopusAPI')
                cls._instance.logger.setLevel(logging.DEBUG)
                
                # Only add handlers if none exist
                if not cls._instance.logger.handlers:
                    # Create handlers
                    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                    console_handler = logging.StreamHandler()
                    
                    # Create formatters and add it to handlers
                    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                    file_handler.setFormatter(log_format)
                    console_handler.setFormatter(log_format)
                    
                    # Add handlers to the logger
                    cls._instance.logger.addHandler(file_handler)
                    cls._instance.logger.addHandler(console_handler)
                
            return cls._instance

    def search(self, search_equation: Union[str, ScopusSearchEquation], count: int = 25, start: int = 0, view: str = "STANDARD", **kwargs) -> Dict[str, Any]:
        """
        Perform a search using a validated ScopusSearchEquation.
        """
        if not isinstance(search_equation, ScopusSearchEquation):
            search_equation = ScopusSearchEquation(search_equation)
        
        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key
        }
        params = {
            "query": str(search_equation),
            "count": count,
            "start": start,
            "view": view
        }
        params.update(kwargs)
        
        self.logger.info(f"Making request to Scopus API with params: {params}")
        response = requests.get(self.BASE_URL, headers=headers, params=params)
        
        self.logger.debug(f"Request URL: {response.url}")
        self.logger.debug(f"Response Status Code: {response.status_code}")
        
        # Log response details before parsing
        if response.status_code == 200:
            response_json = response.json()
            total_results = response_json.get('search-results', {}).get('opensearch:totalResults')
            entries_count = len(response_json.get('search-results', {}).get('entry', []))
            self.logger.info(f"Total results reported by Scopus: {total_results}")
            self.logger.info(f"Number of entries in current response: {entries_count}")
        
        response.raise_for_status()
        if response.status_code == 204:
            self.logger.warning("No content found for the given search equation.")
            raise HTTPError("No content found for the given search equation.")
        if response.status_code == 429:
            self.logger.error("Rate limit exceeded")
            raise HTTPError("Rate limit exceeded. Please try again later.")
        if response.status_code != 200:
            self.logger.error(f"Error {response.status_code}: {response.text}")
            raise HTTPError(f"Error {response.status_code}: {response.text}")
            
        return response.json()

    def search_all(self, search_equation: Union[str, ScopusSearchEquation], total_count: int = 100, view: str = "STANDARD", **kwargs) -> dict:
        """
        Fetches up to total_count results by batching requests (25 per request) and combines them into a single JSON-like dict.
        """
        self.logger.info(f"Starting batch search for {total_count} results")
        all_entries = []
        batch_size = 25
        total_retrieved = 0
        
        for start in range(0, total_count, batch_size):
            self.logger.debug(f"Fetching batch starting at index {start}")
            batch = self.search(search_equation, count=min(batch_size, total_count - start), start=start, view=view, **kwargs)
            entries = batch.get('search-results', {}).get('entry', [])
            
            batch_count = len(entries)
            total_retrieved += batch_count
            self.logger.info(f"Retrieved {batch_count} entries in current batch. Total retrieved so far: {total_retrieved}")
            
            all_entries.extend(entries)
            
            # Get the total available results from the first batch
            if start == 0:
                total_available = int(batch.get('search-results', {}).get('opensearch:totalResults', 0))
                self.logger.info(f"Total results available according to Scopus: {total_available}")
                if total_available < total_count:
                    self.logger.warning(f"Requested {total_count} results but only {total_available} are available")
            
            # Stop if less than batch_size returned (end of results)
            if batch_count < min(batch_size, total_count - start):
                self.logger.info(f"Reached end of results after retrieving {total_retrieved} entries")
                break
        
        # Use the first batch as the base result and update entries
        if 'search-results' in batch:
            self.logger.info(f"Final count of entries retrieved: {len(all_entries)}")
            batch['search-results']['entry'] = all_entries
            
        return batch
