import os
from typing import Dict, List, Optional, Tuple, Set
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

    def get_all_document_ids(self) -> Set[int]:
        """Get all current document IDs from Paperless-NGX"""
        documents = self._make_request("documents/")["results"]
        return {doc["id"] for doc in documents}

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Get a specific document's details"""
        try:
            return self._make_request(f"documents/{doc_id}/")
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 404:
                return None
            raise

    def get_document_file(self, doc_id: int) -> Tuple[bytes, str]:
        """Get the actual document file from Paperless-NGX"""
        url = f"{self.base_url}/api/documents/{doc_id}/download/"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Get filename from Content-Disposition header or use a default
            filename = "document.pdf"
            content_disposition = response.headers.get("Content-Disposition")
            if content_disposition:
                import re
                matches = re.findall('filename="(.+)"', content_disposition)
                if matches:
                    filename = matches[0]
            
            return response.content, filename
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading document from Paperless-NGX: {e}")
            raise

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