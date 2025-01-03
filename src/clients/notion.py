import os
from typing import Dict, List, Optional
from notion_client import Client
from datetime import datetime
from loguru import logger

class NotionClient:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_TOKEN"))
        self.documents_db = os.getenv("NOTION_DOCUMENTS_DB")
        self.tags_db = os.getenv("NOTION_TAGS_DB")
        self.correspondents_db = os.getenv("NOTION_CORRESPONDENTS_DB")

    def create_or_update_document(self, document: Dict) -> Dict:
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
                "Added Date": {"date": {"start": document["added"]}}
            }

            if document.get("correspondent"):
                properties["Correspondent"] = {
                    "relation": [{"id": self._get_correspondent_page_id(document["correspondent"]["id"])}]
                }

            if document.get("tags"):
                properties["Tags"] = {
                    "relation": [{"id": self._get_tag_page_id(tag["id"])} for tag in document["tags"]]
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