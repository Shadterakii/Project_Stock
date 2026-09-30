from .base import CHAIN_COLUMNS, OptionDataProvider


def get_provider(name, **kwargs) -> OptionDataProvider:
    """Build a provider by its config name. Register new providers (e.g. an HK feed) here."""
    if name == "yfinance":
        from .yfinance_provider import YFinanceProvider
        return YFinanceProvider(**kwargs)
    raise ValueError(
        f"Unknown data provider '{name}'. Implement OptionDataProvider in "
        f"option_scanner/providers/ and register it in get_provider()."
    )


__all__ = ["CHAIN_COLUMNS", "OptionDataProvider", "get_provider"]
