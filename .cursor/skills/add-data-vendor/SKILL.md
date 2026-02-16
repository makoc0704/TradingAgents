---
name: add-data-vendor
description: Add a new data vendor or data source to the TradingAgents framework. Use when adding a new financial data API, broker data feed, or alternative data source for stock prices, indicators, fundamentals, or news.
---

# Add a New Data Vendor

## Workflow

```
Task Progress:
- [ ] Step 1: Identify category and methods
- [ ] Step 2: Implement vendor functions
- [ ] Step 3: Register in interface.py
- [ ] Step 4: Update config options
- [ ] Step 5: Write tests
```

## Step 1: Identify Category and Methods

Determine which data category and methods your vendor supports:

| Category | Config Key | Methods |
|----------|-----------|---------|
| Stock Prices (OHLCV) | `core_stock_apis` | `get_stock_data` |
| Technical Indicators | `technical_indicators` | `get_indicators` |
| Fundamentals | `fundamental_data` | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` |
| News & Sentiment | `news_data` | `get_news`, `get_global_news`, `get_insider_sentiment`, `get_insider_transactions` |

A vendor doesn't need to implement all methods in a category.

## Step 2: Implement Vendor Functions

Create `tradingagents/dataflows/<vendor_name>.py`:

```python
"""<Vendor Name> data vendor for TradingAgents."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_stock(ticker: str, curr_date: str) -> str:
    """Fetch OHLCV stock data from <Vendor>.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        curr_date: Reference date in YYYY-MM-DD format.

    Returns:
        CSV-formatted string with columns: Date, Open, High, Low, Close, Volume.

    Raises:
        ConnectionError: If API is unreachable.
        ValueError: If ticker is invalid.
    """
    # Implementation here
    ...
```

**Key requirements:**
- Return type is always `str` (formatted for LLM consumption)
- Use `logging` not `print()`
- Raise specific exceptions for retryable errors (rate limits, timeouts)
- Handle API authentication via environment variables

## Step 3: Register in interface.py

Edit `tradingagents/dataflows/interface.py`:

```python
# 1. Add import at top
from .<vendor_name> import (
    get_stock as get_<vendor>_stock,
    get_indicator as get_<vendor>_indicator,
)

# 2. Add vendor to VENDOR_LIST
VENDOR_LIST = [
    "local", "yfinance", "openai", "google", "<vendor_name>",
]

# 3. Register in VENDOR_METHODS for each supported method
VENDOR_METHODS = {
    "get_stock_data": {
        ...
        "<vendor_name>": get_<vendor>_stock,
    },
}
```

## Step 4: Update Config Options

Add the new vendor as valid option in `tradingagents/default_config.py` comments:

```python
"data_vendors": {
    "core_stock_apis": "yfinance",  # Options: yfinance, alpha_vantage, local, <vendor_name>
}
```

## Step 5: Write Tests

Create `tests/test_dataflows/test_<vendor_name>.py`:
- Mock external API calls
- Test each implemented function returns a non-empty string
- Test error handling (rate limits, invalid tickers, network errors)
- Test that the vendor is correctly routed via `interface.route_to_vendor()`
