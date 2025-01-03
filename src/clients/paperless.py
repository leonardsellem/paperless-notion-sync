import os
from typing import Dict, List, Optional
import requests
from datetime import datetime
from loguru import logger

class PaperlessClient:
    def __init__(self):
        self.base_url = os.getenv("PAPERLESS_URL").rstrip("/")
        self.token = os.getenv("PAPERLESS_TOKEN")
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None) -> dict:
        url = f"{self.base_url}/api/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Paperless-NGX: {e}")
            raise

    def get_documents(self, modified_after: Optional[datetime] = None) -> List[Dict]:
        """Get all documents, optionally filtered by modification date"""
        params = {}
        if modified_after:
            params["modified__after"] = modified_after.isoformat()
        
        return self._make_request("documents/", params=params)["results"]

    def get_tags(self) -> List[Dict]:
        """Get all tags"""
        return self._make_request("tags/")["results"]

    def get_correspondents(self) -> List[Dict]:
        """Get all correspondents"""
        return self._make_request("correspondents/")["results"]

    def get_document_preview(self, doc_id: int) -> bytes:
        """Get document preview/thumbnail"""
        url = f"{self.base_url}/api/documents/{doc_id}/preview/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.content 