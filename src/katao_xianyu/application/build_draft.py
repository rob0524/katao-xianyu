from __future__ import annotations

from dataclasses import dataclass

from katao_xianyu.application.ports import WinSource
from katao_xianyu.domain.models import ListingDraft, WonCard
from katao_xianyu.domain.pricing import suggest_price_fen
from katao_xianyu.domain.title import build_content, build_title


@dataclass(frozen=True)
class PricingConfig:
    markup_ratio: float = 1.35
    markup_fen: int = 0
    stuff_status: int = 0


class BuildDraft:
    def __init__(self, wins: WinSource, pricing: PricingConfig | None = None) -> None:
        self._wins = wins
        self._pricing = pricing or PricingConfig()

    def from_card(self, card: WonCard) -> ListingDraft:
        title = build_title(card.identity, fallback=card.external_id)
        content = build_content(card)
        price = suggest_price_fen(
            card.cost_fen,
            markup_ratio=self._pricing.markup_ratio,
            markup_fen=self._pricing.markup_fen,
        )
        # Listing images stay empty until PrepareListingImage supplies cropped public URLs.
        # Never put watermarked CardHobby source URLs into image_urls.
        return ListingDraft(
            external_id=card.external_id,
            source_task=card.source_task,
            title=title,
            content=content,
            image_urls=(),
            price_fen=price,
            cost_fen=card.cost_fen,
            auction_title=card.auction_title,
            source_image_url=card.source_image_url,
            stuff_status=self._pricing.stuff_status,
            outer_id=card.external_id,
        )

    def execute(self, external_id: str) -> ListingDraft:
        card = self._wins.get_win(external_id)
        if card is None:
            raise KeyError(f"win not found: {external_id}")
        return self.from_card(card)
