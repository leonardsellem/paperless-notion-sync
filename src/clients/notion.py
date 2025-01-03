import os
from typing import Dict, List, Optional, Set
from notion_client import Client
from datetime import datetime
from loguru import logger
import requests

class NotionClient:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_TOKEN"))
        self.documents_db = os.getenv("NOTION_DOCUMENTS_DB")
        self.tags_db = os.getenv("NOTION_TAGS_DB")
        self.correspondents_db = os.getenv("NOTION_CORRESPONDENTS_DB")

    def create_or_update_document(self, document: Dict, document_file: bytes = None, filename: str = None) -> Dict:
        """Create or update a document in Notion"""
        try:
            # Check if document already exists
            results = self.client.databases.query(
                database_id=self.documents_db,
                filter={
                    "property": "paperless_id",
                    "number": {"equals": document["id"]}
                }
            )

            properties = {
                "Title": {"title": [{"text": {"content": document["title"]}}]},
                "paperless_id": {"number": document["id"]},
                "Created Date": {"date": {"start": document["created"]}},
                "Added Date": {"date": {"start": document["added"]}},
                "Archived": {"checkbox": False}  # Set document as not archived
            }

            if document.get("correspondent"):
                properties["Correspondent"] = {
                    "relation": [{"id": self._get_correspondent_page_id(document["correspondent"]["id"])}]
                }

            if document.get("tags"):
                properties["Tags"] = {
                    "relation": [{"id": self._get_tag_page_id(tag["id"])} for tag in document["tags"]]
                }

            # Handle file upload if provided
            if document_file and filename:
                # First, upload the file to Notion's S3
                upload_response = self._upload_file_to_notion(document_file, filename)
                
                # Add file property
                properties["File"] = {
                    "files": [{
                        "type": "external",
                        "name": filename,
                        "external": {
                            "url": upload_response["url"]
                        }
                    }]
                }

            if results["results"]:
                # Update existing page
                return self.client.pages.update(
                    page_id=results["results"][0]["id"],
                    properties=properties
                )
            else:
                # Create new page
                return self.client.pages.create(
                    parent={"database_id": self.documents_db},
                    properties=properties
                )
        except Exception as e:
            logger.error(f"Error creating/updating document in Notion: {e}")
            raise

    def get_all_document_ids(self) -> Dict[int, str]:
        """Get all document IDs and their page IDs from Notion"""
        documents = {}
        has_more = True
        start_cursor = None

        while has_more:
            response = self.client.databases.query(
                database_id=self.documents_db,
                start_cursor=start_cursor
            )
            
            for page in response["results"]:
                try:
                    paperless_id = page["properties"]["paperless_id"]["number"]
                    if paperless_id:
                        documents[paperless_id] = page["id"]
                except (KeyError, TypeError):
                    continue

            has_more = response["has_more"]
            start_cursor = response["next_cursor"] if has_more else None

        return documents

    def archive_document(self, page_id: str) -> None:
        """Mark a document as archived in Notion"""
        try:
            self.client.pages.update(
                page_id=page_id,
                properties={
                    "Archived": {"checkbox": True}
                }
            )
            logger.debug(f"Archived document with page ID: {page_id}")
        except Exception as e:
            logger.error(f"Error archiving document in Notion: {e}")
            raise

    def _upload_file_to_notion(self, file_content: bytes, filename: str) -> Dict:
        """Upload a file to Notion's S3 storage"""
        try:
            # Get upload URL from Notion
            response = self.client.files.upload({
                "filename": filename,
                "type": "pdf"  # Assuming PDF files from Paperless-NGX
            })

            # Upload the file to the provided S3 URL
            upload_url = response["upload_url"]
            s3_response = requests.put(
                upload_url,
                data=file_content,
                headers={"Content-Type": "application/pdf"}
            )
            s3_response.raise_for_status()

            return response
        except Exception as e:
            logger.error(f"Error uploading file to Notion: {e}")
            raise

    def create_or_update_tag(self, tag: Dict) -> Dict:
        """Create or update a tag in Notion"""
        try:
            results = self.client.databases.query(
                database_id=self.tags_db,
                filter={
                    "property": "paperless_id",
                    "number": {"equals": tag["id"]}
                }
            )

            properties = {
                "Name": {"title": [{"text": {"content": tag["name"]}}]},
                "paperless_id": {"number": tag["id"]},
                "Color": {"rich_text": [{"text": {"content": tag.get("color", "")}}]}
            }

            if results["results"]:
                return self.client.pages.update(
                    page_id=results["results"][0]["id"],
                    properties=properties
                )
            else:
                return self.client.pages.create(
                    parent={"database_id": self.tags_db},
                    properties=properties
                )
        except Exception as e:
            logger.error(f"Error creating/updating tag in Notion: {e}")
            raise

    def create_or_update_correspondent(self, correspondent: Dict) -> Dict:
        """Create or update a correspondent in Notion"""
        try:
            results = self.client.databases.query(
                database_id=self.correspondents_db,
                filter={
                    "property": "paperless_id",
                    "number": {"equals": correspondent["id"]}
                }
            )

            properties = {
                "Name": {"title": [{"text": {"content": correspondent["name"]}}]},
                "paperless_id": {"number": correspondent["id"]}
            }

            if results["results"]:
                return self.client.pages.update(
                    page_id=results["results"][0]["id"],
                    properties=properties
                )
            else:
                return self.client.pages.create(
                    parent={"database_id": self.correspondents_db},
                    properties=properties
                )
        except Exception as e:
            logger.error(f"Error creating/updating correspondent in Notion: {e}")
            raise

    def _get_tag_page_id(self, paperless_id: int) -> str:
        """Get Notion page ID for a tag by its Paperless ID"""
        results = self.client.databases.query(
            database_id=self.tags_db,
            filter={"property": "paperless_id", "number": {"equals": paperless_id}}
        )
        if not results["results"]:
            raise ValueError(f"Tag with Paperless ID {paperless_id} not found in Notion")
        return results["results"][0]["id"]

    def _get_correspondent_page_id(self, paperless_id: int) -> str:
        """Get Notion page ID for a correspondent by its Paperless ID"""
        results = self.client.databases.query(
            database_id=self.correspondents_db,
            filter={"property": "paperless_id", "number": {"equals": paperless_id}}
        )
        if not results["results"]:
            raise ValueError(f"Correspondent with Paperless ID {paperless_id} not found in Notion")
        return results["results"][0]["id"] 