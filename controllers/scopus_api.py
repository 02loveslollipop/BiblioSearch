import requests
import threading
from typing import Dict, Any, Union
from requests.exceptions import HTTPError
from models import ScopusSearchEquation

import logging

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
        response = requests.get(self.BASE_URL, headers=headers, params=params)
        logging.debug(f"Request URL: {response.url}")
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")
        response.raise_for_status()
        if response.status_code == 204:
            raise HTTPError("No content found for the given search equation.")
        if response.status_code == 429:
            raise HTTPError("Rate limit exceeded. Please try again later.")
        if response.status_code != 200:
            raise HTTPError(f"Error {response.status_code}: {response.text}")
        return response.json()

    def search_all(self, search_equation: Union[str, ScopusSearchEquation], total_count: int = 100, view: str = "STANDARD", **kwargs) -> dict:
        """
        Fetches up to total_count results by batching requests (25 per request) and combines them into a single JSON-like dict.
        """
        all_entries = []
        batch_size = 25
        for start in range(0, total_count, batch_size):
            batch = self.search(search_equation, count=min(batch_size, total_count - start), start=start, view=view, **kwargs)
            entries = batch.get('search-results', {}).get('entry', [])
            all_entries.extend(entries)
            # Stop if less than batch_size returned (end of results)
            if len(entries) < min(batch_size, total_count - start):
                break
        # Use the first batch as the base result
        if 'search-results' in batch:
            batch['search-results']['entry'] = all_entries
        return batch
