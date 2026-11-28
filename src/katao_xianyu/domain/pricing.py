from __future__ import annotations


def suggest_price_fen(
    cost_fen: int,
    *,
    markup_ratio: float = 1.35,
    markup_fen: int = 0,
) -> int:
    """Suggest listing price in fen. Never below cost."""
    if cost_fen <= 0:
        return max(1, markup_fen)
    priced = int(round(cost_fen * markup_ratio)) + max(0, markup_fen)
    return max(cost_fen, priced, 1)
