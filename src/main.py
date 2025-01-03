import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
from clients.paperless import PaperlessClient
from clients.notion import NotionClient

def setup_logging():
    """Configure logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        "sync.log",
        rotation="1 day",
        retention="7 days",
        level=log_level
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
        documents = self.paperless.get_documents(modified_after=self.last_sync)
        for document in documents:
            try:
                self.notion.create_or_update_document(document)
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