# Paperless-NGX to Notion Sync

This service synchronizes documents, tags, and correspondents from Paperless-NGX to Notion databases.

## Features

- Syncs documents with metadata (title, date, correspondent, tags)
- Syncs tags with their properties
- Syncs correspondents
- Incremental updates (only syncs changed items)
- Configurable sync interval
- Docker support for easy deployment

## Prerequisites

1. A running Paperless-NGX instance
2. A Notion account with:
   - A Notion integration (for API access)
   - Three databases set up for Documents, Tags, and Correspondents

## Setup

1. Clone this repository
2. Copy the environment file:
   ```bash
   cp config/.env.example config/.env
   ```

3. Edit `config/.env` and fill in your configuration:
   - `PAPERLESS_URL`: Your Paperless-NGX instance URL
   - `PAPERLESS_TOKEN`: Your Paperless-NGX API token
   - `NOTION_TOKEN`: Your Notion integration token
   - `NOTION_DOCUMENTS_DB`: Notion database ID for documents
   - `NOTION_TAGS_DB`: Notion database ID for tags
   - `NOTION_CORRESPONDENTS_DB`: Notion database ID for correspondents
   - `SYNC_INTERVAL`: Sync interval in seconds (default: 3600)
   - `LOG_LEVEL`: Logging level (default: INFO)

## Notion Database Setup

Create three databases in Notion with the following properties:

### Documents Database
- Title (title)
- paperless_id (number)
- Created Date (date)
- Added Date (date)
- Correspondent (relation to Correspondents database)
- Tags (relation to Tags database)

### Tags Database
- Name (title)
- paperless_id (number)
- Color (text)

### Correspondents Database
- Name (title)
- paperless_id (number)

## Running with Docker

1. Make sure Docker and Docker Compose are installed
2. Build and start the service:
   ```bash
   docker-compose up -d
   ```

3. Check the logs:
   ```bash
   docker-compose logs -f
   ```

## Running without Docker

1. Install Python 3.11 or later
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the service:
   ```bash
   python src/main.py
   ```

## Monitoring

The service creates a `sync.log` file with detailed logging information. The log file is rotated daily and kept for 7 days.

## Troubleshooting

1. Check the logs in `sync.log`
2. Verify your environment variables in `config/.env`
3. Ensure your Paperless-NGX instance is accessible
4. Verify your Notion integration has access to the databases 