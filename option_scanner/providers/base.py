"""Data-provider interface. Add a new market/source by subclassing OptionDataProvider."""
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

# Columns every provider's get_chain() must return.
CHAIN_COLUMNS = ["type", "strike", "bid", "ask", "last", "volume", "open_interest"]


class OptionDataProvider(ABC):
    name = "base"

    @abstractmethod
    def get_price_history(self, ticker: str, period: str) -> pd.Series:
        """Daily closing prices (oldest first). The last value is used as spot."""

    @abstractmethod
    def get_expiries(self, ticker: str) -> list[date]:
        """Available option expiration dates."""

    @abstractmethod
    def get_chain(self, ticker: str, expiry: date) -> pd.DataFrame:
        """Calls and puts for one expiry with CHAIN_COLUMNS ('type' is 'call' or 'put')."""

    def get_dividend_yield(self, ticker: str) -> float:
        """Annual continuous dividend yield as a fraction. Default 0."""
        return 0.0
