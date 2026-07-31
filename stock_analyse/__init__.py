"""stock_analyse: 简单的股票行情工具 (simple stock market-quote toolkit)."""

from .quotes import Quote, QuoteError, fetch_quote, fetch_quotes

__all__ = ["Quote", "QuoteError", "fetch_quote", "fetch_quotes"]
__version__ = "0.1.0"
