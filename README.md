# AutoFeeder

A data pipeline that monitors USDA feeder cattle market reports, fetches live auction data, and stores aggregated results in a PostgreSQL database.

## What It Does

AutoFeeder polls the [USDA My Market News (MMN) API](https://marsapi.ams.usda.gov) on a configurable interval, detects when new reports are published, fetches detailed cattle sale data, and upserts aggregated market reports into a PostgreSQL database.

It tracks **steers** (medium/large frame, grades 1-2) across:

- **Market types**: live auction, video auction, direct sales
- **Regions**: North Central, South Central
- **Weight classes**: 700–749, 750–799, 800–849, 850–899 lbs
- **Metrics per class**: head count, average weight, average price

## Architecture

The project follows a clean layered architecture:

```text
app/
├── domain/
│   └── models/         # Core entities: Auction, Report, StoredReport, Schemas
├── infrastructure/
│   ├── api_client.py   # Async USDA MMN API client
│   ├── database.py     # SQLAlchemy async session factory
│   └── transformers.py # Aggregates raw API data into weight-class reports
├── services/
│   └── report_monitor.py  # Main polling orchestrator
├── utils/
│   ├── enums.py        # Region, MarketType, ReportStatus
│   ├── validators.py   # Input validation helpers
│   └── exceptions.py   # Custom exception types
├── config.py           # Pydantic Settings (loaded from .env)
├── logger.py           # Structured JSON logging via loguru
└── main.py             # Typer CLI entry point
```

**Main polling loop:**

1. Fetch current report listings from the MMN API
2. Compare against stored reports in the DB to detect changes
3. For each changed report, fetch and transform detailed sale data
4. Upsert results into `reports` and `stored_reports` tables
5. Wait for the configured polling interval, then repeat

## Requirements

- Python 3.12+
- PostgreSQL
- [Poetry](https://python-poetry.org/)

## Setup

### 1. Install dependencies

```bash
poetry install
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
ENV=development
LOG_LEVEL=DEBUG
APP_NAME=autofeeder
APP_VERSION=0.1.0

# USDA My Market News API
MMN_BASE_URL=https://marsapi.ams.usda.gov/services
MMN_API_VERSION=v3.1
MMN_API_KEY=your_api_key_here

# Polling
POLLING_INTERVAL=15
POLLING_MAX_RETRIES=3
POLLING_RETRY_BACKOFF=5
DEFAULT_REQUEST_TIMEOUT=30

# Database
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_PORT=5432
DB_NAME=postgres
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

> A USDA MMN API key can be obtained at [https://marsapi.ams.usda.gov](https://marsapi.ams.usda.gov).

### 3. Run migrations

```bash
poetry run alembic upgrade head
```

### 4. Start the application

```bash
poetry run python -m app.main run
```

## Testing

```bash
# Run all tests
poetry run pytest tests

# Run a subset by path
poetry run pytest tests/infrastructure

# Run only integration tests (requires live DB and API)
poetry run pytest -vv -m integration

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Shorthand via custom script
poetry run test auction
```

Unit tests use mocked API and DB calls. Integration tests (marked `@pytest.mark.integration`) hit a live database and the USDA API.

## Type Checking

```bash
mypy --config-file pyproject.toml app/
```

## Tech Stack

| Component       | Library                          |
| --------------- | -------------------------------- |
| ORM             | SQLModel + SQLAlchemy 2.0 (async)|
| Database driver | asyncpg                          |
| Migrations      | Alembic                          |
| HTTP client     | aiohttp                          |
| Validation      | Pydantic v2                      |
| CLI             | Typer                            |
| Logging         | loguru (structured JSON)         |
| Testing         | pytest + pytest-asyncio          |
| Type checking   | mypy                             |
