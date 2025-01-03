import os
from typing import Dict, List, Optional, Set
from notion_client import Client
from datetime import datetime
from loguru import logger
import requests
import json

class NotionClient:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_TOKEN"))
        self.documents_db = os.getenv("NOTION_DOCUMENTS_DB")
        self.tags_db = os.getenv("NOTION_TAGS_DB")
        self.correspondents_db = os.getenv("NOTION_CORRESPONDENTS_DB")

    def create_or_update_document(self, document: Dict, document_file: bytes = None, filename: str = None) -> Dict:
        """Create or update a document in Notion"""
        try:
            # Debug log the document structure and type
            logger.debug(f"Document type: {type(document)}")
            logger.debug(f"Document data: {json.dumps(document, indent=2, default=str)}")
            
            # Validate document structure
            if not isinstance(document, dict):
                raise ValueError(f"Document is not a dictionary, it is a {type(document)}")
            if 'id' not in document:
                raise ValueError("Document does not contain 'id'")

            # Log document ID and type
            logger.debug(f"Document ID: {document['id']} (type: {type(document['id'])})")

            # Check if document already exists
            try:
                results = self.client.databases.query(
                    database_id=self.documents_db,
                    filter={
                        "property": "paperless_id",
                        "number": {"equals": document["id"]}
                    }
                )
                logger.debug(f"Query results type: {type(results)}")
                logger.debug(f"Query results: {json.dumps(results, indent=2)}")
            except Exception as e:
                logger.error(f"Error querying database: {e}")
                raise

            # Convert dates to ISO format if they're not already
            created_date = document.get("created", "")
            logger.debug(f"Created date before processing: {created_date} (type: {type(created_date)})")
            
            if isinstance(created_date, (int, float)):
                created_date = datetime.fromtimestamp(created_date).isoformat()
            elif isinstance(created_date, str):
                try:
                    created_date = datetime.fromisoformat(created_date).isoformat()
                except ValueError:
                    created_date = None
            
            added_date = document.get("added", "")
            logger.debug(f"Added date before processing: {added_date} (type: {type(added_date)})")
            
            if isinstance(added_date, (int, float)):
                added_date = datetime.fromtimestamp(added_date).isoformat()
            elif isinstance(added_date, str):
                try:
                    added_date = datetime.fromisoformat(added_date).isoformat()
                except ValueError:
                    added_date = None

            # Debug log the processed dates
            logger.debug(f"Processed dates - created: {created_date}, added: {added_date}")

            properties = {
                "Title": {"title": [{"text": {"content": str(document.get("title", "Untitled"))}}]},
                "paperless_id": {"number": document["id"]},
            }

            if created_date:
                properties["Created Date"] = {"date": {"start": created_date}}
            if added_date:
                properties["Added Date"] = {"date": {"start": added_date}}
            
            properties["Archived"] = {"checkbox": False}

            # Debug log the properties
            logger.debug(f"Properties before relations: {json.dumps(properties, indent=2)}")

            if document.get("correspondent"):
                try:
                    logger.debug(f"Correspondent data: {json.dumps(document['correspondent'], indent=2)}")
                    correspondent_data = document["correspondent"]
                    if isinstance(correspondent_data, (int, str)):
                        correspondent_id = self._get_correspondent_page_id(int(correspondent_data))
                    else:
                        correspondent_id = self._get_correspondent_page_id(correspondent_data.get("id"))
                    properties["Correspondent"] = {
                        "relation": [{"id": correspondent_id}]
                    }
                except Exception as e:
                    logger.warning(f"Could not link correspondent: {e}")

            if document.get("tags"):
                try:
                    logger.debug(f"Tags data: {json.dumps(document['tags'], indent=2)}")
                    tag_ids = []
                    for tag in document["tags"]:
                        if isinstance(tag, (int, str)):
                            tag_id = self._get_tag_page_id(int(tag))
                        else:
                            tag_id = self._get_tag_page_id(tag.get("id"))
                        tag_ids.append(tag_id)
                    
                    if tag_ids:
                        properties["Tags"] = {
                            "relation": [{"id": tag_id} for tag_id in tag_ids]
                        }
                except Exception as e:
                    logger.warning(f"Could not link tags: {e}")

            # Handle file upload if provided
            if document_file and filename:
                try:
                    # Get file properties with document ID
                    file_props = self._upload_file_to_notion(document_file, filename, document["id"])
                    logger.debug(f"File properties: {json.dumps(file_props, indent=2)}")
                    
                    # Add file property
                    properties["File"] = {
                        "files": [{
                            "type": "external",
                            "name": file_props["name"],
                            "external": {
                                "url": file_props["url"]
                            }
                        }]
                    }
                except Exception as e:
                    logger.warning(f"Could not handle file: {e}")

            # Debug log final properties
            logger.debug(f"Final properties: {json.dumps(properties, indent=2)}")

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

    def _upload_file_to_notion(self, file_content: bytes, filename: str, document_id: int) -> Dict:
        """Create a direct URL to the document in Paperless-NGX"""
        try:
            # Use the actual Paperless-NGX download URL
            paperless_url = os.getenv("PAPERLESS_URL").rstrip("/")
            download_url = f"{paperless_url}/api/documents/{document_id}/download/"
            
            # Truncate filename if it's too long (Notion has a 100-char limit)
            if len(filename) > 100:
                name, ext = os.path.splitext(filename)
                # Leave room for the extension and ellipsis
                max_name_length = 96 - len(ext)  # 100 - 3 (...) - len(ext)
                truncated_name = name[:max_name_length] + "..."
                display_name = truncated_name + ext
                logger.debug(f"Truncated filename from {filename} to {display_name}")
            else:
                display_name = filename
            
            properties = {
                "url": download_url,
                "name": display_name
            }
            
            return properties
        except Exception as e:
            logger.error(f"Error handling file for Notion: {e}")
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
        # Ensure paperless_id is an integer
        if isinstance(paperless_id, dict):
            paperless_id = paperless_id.get('id')
        paperless_id = int(paperless_id)
        
        logger.debug(f"Getting tag page ID for paperless_id: {paperless_id}")
        results = self.client.databases.query(
            database_id=self.tags_db,
            filter={"property": "paperless_id", "number": {"equals": paperless_id}}
        )
        if not results["results"]:
            raise ValueError(f"Tag with Paperless ID {paperless_id} not found in Notion")
        return results["results"][0]["id"]

    def _get_correspondent_page_id(self, paperless_id: int) -> str:
        """Get Notion page ID for a correspondent by its Paperless ID"""
        # Ensure paperless_id is an integer
        if isinstance(paperless_id, dict):
            paperless_id = paperless_id.get('id')
        paperless_id = int(paperless_id)
        
        logger.debug(f"Getting correspondent page ID for paperless_id: {paperless_id}")
        results = self.client.databases.query(
            database_id=self.correspondents_db,
            filter={"property": "paperless_id", "number": {"equals": paperless_id}}
        )
        if not results["results"]:
            raise ValueError(f"Correspondent with Paperless ID {paperless_id} not found in Notion")
        return results["results"][0]["id"] 