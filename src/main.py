import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
from clients.paperless import PaperlessClient
from clients.notion import NotionClient

def setup_logging():
    """Configure logging"""
    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    logger.remove()
    
    # Create logs directory if it doesn't exist
    os.makedirs("/app/logs", exist_ok=True)
    
    logger.add(
        "/app/logs/sync.log",
        rotation="1 day",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    logger.add(lambda msg: print(msg), level=log_level)

class PaperlessNotionSync:
    def __init__(self):
        self.paperless = PaperlessClient()
        self.notion = NotionClient()
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", 3600))
        self.last_sync = None

    def sync_correspondents(self):
        """Sync all correspondents from Paperless to Notion"""
        logger.info("Syncing correspondents...")
        correspondents = self.paperless.get_correspondents()
        for correspondent in correspondents:
            try:
                self.notion.create_or_update_correspondent(correspondent)
                logger.debug(f"Synced correspondent: {correspondent['name']}")
            except Exception as e:
                logger.error(f"Error syncing correspondent {correspondent['name']}: {e}")

    def sync_tags(self):
        """Sync all tags from Paperless to Notion"""
        logger.info("Syncing tags...")
        tags = self.paperless.get_tags()
        for tag in tags:
            try:
                self.notion.create_or_update_tag(tag)
                logger.debug(f"Synced tag: {tag['name']}")
            except Exception as e:
                logger.error(f"Error syncing tag {tag['name']}: {e}")

    def sync_documents(self):
        """Sync documents from Paperless to Notion"""
        logger.info("Syncing documents...")
        
        # Get all current document IDs from both systems
        paperless_doc_ids = self.paperless.get_all_document_ids()
        notion_docs = self.notion.get_all_document_ids()
        notion_doc_ids = set(notion_docs.keys())

        # Find deleted documents
        deleted_doc_ids = notion_doc_ids - paperless_doc_ids
        for doc_id in deleted_doc_ids:
            try:
                self.notion.archive_document(notion_docs[doc_id])
                logger.info(f"Archived document with ID {doc_id} in Notion")
            except Exception as e:
                logger.error(f"Error archiving document {doc_id}: {e}")

        # Get modified documents since last sync
        documents = self.paperless.get_documents(modified_after=self.last_sync)
        
        # Update or create documents
        for document in documents:
            try:
                # Get the document file
                file_content, filename = self.paperless.get_document_file(document["id"])
                
                # Create or update the document in Notion with the file
                self.notion.create_or_update_document(
                    document=document,
                    document_file=file_content,
                    filename=filename
                )
                logger.debug(f"Synced document: {document['title']}")
            except Exception as e:
                logger.error(f"Error syncing document {document['title']}: {e}")

    def run(self):
        """Main sync loop"""
        logger.info("Starting Paperless-Notion sync service")
        
        while True:
            try:
                # First sync correspondents and tags (they're needed for document relations)
                self.sync_correspondents()
                self.sync_tags()
                
                # Then sync documents
                self.sync_documents()
                
                self.last_sync = datetime.now()
                logger.info(f"Sync completed. Next sync in {self.sync_interval} seconds")
                
                # Wait for next sync interval
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error during sync: {e}")
                # Wait a bit before retrying
                time.sleep(60)

def main():
    # Load environment variables
    load_dotenv("config/.env")
    
    # Setup logging
    setup_logging()
    
    # Start sync service
    sync_service = PaperlessNotionSync()
    sync_service.run()

if __name__ == "__main__":
    main() 