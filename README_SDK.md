# Delta9 Intelligence SDK

This SDK allows you to programmatically access the Delta9 lead generation engine, run searches, and manage scrapers.

## Installation

You can install the SDK locally:

```bash
pip install -e .
```

## Usage

### Basic Search

```python
from app.sdk import Delta9

# Initialize the SDK
with Delta9() as delta9:
    # Run a search
    leads = delta9.search(
        query="maize suppliers",
        location="Nairobi",
        limit=10
    )
    
    for lead in leads:
        print(f"Found: {lead.buyer_name} - {lead.contact_phone}")
```

### Managing Scrapers

```python
from app.sdk import Delta9

with Delta9() as delta9:
    # List active scrapers
    print(delta9.get_scrapers())
    
    # Enable a specific scraper
    delta9.enable_scraper("GoogleMapsScraper")
    
    # Disable a scraper
    delta9.disable_scraper("TwitterScraper")
```

### Retrieving Saved Leads

```python
from app.sdk import Delta9

with Delta9() as delta9:
    # Get last 50 leads
    leads = delta9.get_leads(limit=50, verified_only=True)
```

## Configuration

The SDK relies on environment variables for database connection and API keys. Ensure your `.env` file is set up or variables are exported.

- `DATABASE_URL`: Connection string for the database.
- `OPENAI_API_KEY`: Required for NLP features.
- Scraper keys (e.g., `SERPAPI_KEY`, `GOOGLE_CSE_ID`) as needed.
