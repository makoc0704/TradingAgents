"""Universe definitions — static ticker lists with predefined presets.

No dynamic screening. The ``resolve_universe`` helper accepts either a
preset name or a plain list and always returns ``List[str]``.
"""

from typing import List, Union

UNIVERSE_PRESETS = {
    "magnificent_7": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    ],
    "sp500_tech_10": [
        "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "CSCO", "ACN",
    ],
    "diversified_5": [
        "AAPL", "JPM", "JNJ", "XOM", "PG",
    ],
    "faang": [
        "META", "AMZN", "AAPL", "NFLX", "GOOGL",
    ],
}


def resolve_universe(name_or_list: Union[str, List[str]]) -> List[str]:
    """Resolve a universe specification to a concrete list of tickers.

    Args:
        name_or_list: Either a preset name (e.g. ``"magnificent_7"``) or
            an explicit list of ticker symbols (e.g. ``["AAPL", "NVDA"]``).

    Returns:
        Deduplicated, uppercased list of ticker symbols.

    Raises:
        ValueError: If a preset name is given but not found.
    """
    if isinstance(name_or_list, list):
        seen = set()
        result = []
        for t in name_or_list:
            upper = t.upper()
            if upper not in seen:
                seen.add(upper)
                result.append(upper)
        return result

    name = name_or_list.lower().strip()
    if name not in UNIVERSE_PRESETS:
        available = ", ".join(sorted(UNIVERSE_PRESETS.keys()))
        raise ValueError(
            f"Unknown universe preset '{name_or_list}'. "
            f"Available presets: {available}"
        )
    return list(UNIVERSE_PRESETS[name])
