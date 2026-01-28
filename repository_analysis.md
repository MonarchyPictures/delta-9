# Repository Analysis: Delta-9

## Overview
This repository contains a full-stack application (Buying Intent Radar system) with a Python backend and a Vite/React frontend.

## Project Structure
- **Root Directory**: Contains entry points (`main.py`, `scraper.py`), setup scripts (`seed_db.py`, `reset_db.py`), and a large suite of test scripts (`test_*.py`).
- **`/app` (Backend)**:
  - `core/`: Business logic, including Celery workers and compliance.
  - `db/`: Database models and connection management (SQLAlchemy).
  - `nlp/`: Intelligence services for intent detection, duplicate detection, and demand forecasting.
  - `scrapers/`: Web scraping infrastructure.
- **`/frontend`**:
  - React/JSX application managed with Vite.
  - Tailwind CSS integration.
  - View-based architecture (Dashboard, Agents, Leads, Radar).

## Key Components
- **Main Entry**: `main.py` (Root and app/main.py).
- **Dependencies**: Managed via `requirements.txt` (Backend) and `package.json` (Frontend).
- **Core Documentation**: `VIEW_PROTOCOL.md`.

## Commit Status
- **Latest Commit**: `8068122` - Complete system audit and fixes: standardized frontend API URLs, fixed Leads page UI, implemented strict buyer-intent classification.
- **Branch**: `main` (Synchronized with remote).