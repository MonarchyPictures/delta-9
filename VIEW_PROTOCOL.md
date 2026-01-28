# Delta9 View Protocol

This document outlines the standard view and interaction protocols for the Delta9 platform.

## 1. Role & Mission
Delta9 is a Buyer-Intent Enforcement AI. Its primary mission is to identify and surface people who are ACTIVELY LOOKING TO BUY a product or service.

### Non-Negotiable Rules
- **ZERO Seller Leakage**: Any post containing seller signals (for sale, selling, available, price, etc.) MUST be discarded unless it's a "who sells?" type question.
- **Mandatory Buyer Signals**: Accepted leads MUST contain clear buyer language in English or Swahili (e.g., "looking for", "natafuta", "need urgently").
- **100% Certainty**: If intent is unclear, the lead MUST be rejected.

## 2. Lead Discovery Protocol
- **Discovery Radius**: Configurable per agent (Default: 50km).
- **Min Confidence**: Threshold for lead acceptance (Default: 0.7/70%).
- **Verification Logic**: Leads are scored based on platform credibility, contact info verification, and intent specificity.

## 3. UI/UX Standards
- **High Intent Signals**: Leads with intent scores > 0.8 are marked with a "FLAME" icon and "Buying Now" badge.
- **Lead Discarding**: Users can discard leads using the "Trash" icon, which removes them from the database.
- **WhatsApp Integration**: Prioritize direct WhatsApp links with pre-filled buyer-intent messages.

## 5. System Connectivity & Fallbacks
- **Frontend Access**: Always use `http://127.0.0.1:3000` to avoid `localhost` resolution issues in some environments.
- **Backend Access**: Standardized at `http://127.0.0.1:8000`.
- **Connectivity Issues**:
  - `net::ERR_ABORTED`: Often caused by server restarts or HMR timeouts. Refresh the page.
  - `net::ERR_CONNECTION_REFUSED`: Ensure both backend and frontend servers are running in the terminal.
- **Redis Status**:
  - When Redis is "Offline", the system automatically switches to `sqlite` for the task broker.
  - Background scraping will still function, but might be slightly slower.
  - Real-time notifications continue to work via the polling mechanism.

## 6. View & Data Integrity
- **Stale Data**: If the UI shows "No Active Signals Found" unexpectedly, check the "Radar" view to ensure agents are active.
- **Lead Management**:
  - **Discarding**: Clicking the "Trash" icon sends a `DELETE` request to the backend, permanently removing the lead and all its notification signals from the database.
  - **Saving**: Clicking the "Bookmark" icon toggles the `is_saved` status, allowing you to filter for these leads later.
- **Intent Certainty**: All discovered leads must meet the 100% certainty rule defined in the Role & Mission section.
