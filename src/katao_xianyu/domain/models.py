from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PublishStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    LISTED = "listed"
    PUBLISH_FAILED = "publish_failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CardIdentity:
    year: str = ""
    year_raw: str = ""
    brand: str = ""
    series: str = ""
    series_display: str = ""
    players: tuple[str, ...] = ()
    player_query: str = ""
    teams: tuple[str, ...] = ()
    serial: str = ""
    print_run: str | None = None
    parallel: tuple[str, ...] = ()
    parallel_phrases: tuple[str, ...] = ()
    signed: bool = False
    attribute_form: str = ""
    grading: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CardIdentity:
        if not data:
            return cls()
        players = data.get("players") or []
        teams = data.get("teams") or []
        parallel = data.get("parallel") or []
        parallel_phrases = data.get("parallel_phrases") or []
        return cls(
            year=str(data.get("year") or ""),
            year_raw=str(data.get("year_raw") or ""),
            brand=str(data.get("brand") or ""),
            series=str(data.get("series") or ""),
            series_display=str(data.get("series_display") or data.get("series") or ""),
            players=tuple(str(p) for p in players),
            player_query=str(data.get("player_query") or ""),
            teams=tuple(str(t) for t in teams),
            serial=str(data.get("serial") or ""),
            print_run=(
                str(data["print_run"]) if data.get("print_run") is not None else None
            ),
            parallel=tuple(str(p) for p in parallel),
            parallel_phrases=tuple(str(p) for p in parallel_phrases),
            signed=bool(data.get("signed")),
            attribute_form=str(data.get("attribute_form") or ""),
            grading=(
                str(data["grading"]) if data.get("grading") is not None else None
            ),
            raw=dict(data),
        )


@dataclass(frozen=True)
class WonCard:
    """A real auction win enriched with scan-side image/identity."""

    external_id: str
    source_task: str
    auction_title: str
    cost_yuan: float
    image_url: str  # CardHobby source image (may have seller watermark)
    identity: CardIdentity
    auction_link: str = ""
    payment_due: str = ""
    final_price_raw: str = ""

    @property
    def cost_fen(self) -> int:
        return max(0, int(round(self.cost_yuan * 100)))

    @property
    def source_image_url(self) -> str:
        """Alias: auction CDN URL before card-face crop."""
        return self.image_url


@dataclass(frozen=True)
class ListingDraft:
    """Publish-ready copy. Title/content never copy auction watermark titles."""

    external_id: str
    source_task: str
    title: str
    content: str
    image_urls: tuple[str, ...]  # listing images only (cropped public URLs)
    price_fen: int
    cost_fen: int
    auction_title: str
    source_image_url: str = ""  # original CardHobby URL for reference
    stuff_status: int = 0
    outer_id: str = ""

    def with_overrides(
        self,
        *,
        title: str | None = None,
        content: str | None = None,
        price_fen: int | None = None,
        stuff_status: int | None = None,
        image_urls: tuple[str, ...] | None = None,
    ) -> ListingDraft:
        return ListingDraft(
            external_id=self.external_id,
            source_task=self.source_task,
            title=title if title is not None else self.title,
            content=content if content is not None else self.content,
            image_urls=image_urls if image_urls is not None else self.image_urls,
            price_fen=price_fen if price_fen is not None else self.price_fen,
            cost_fen=self.cost_fen,
            auction_title=self.auction_title,
            source_image_url=self.source_image_url,
            stuff_status=(
                stuff_status if stuff_status is not None else self.stuff_status
            ),
            outer_id=self.outer_id or self.external_id,
        )


@dataclass
class PublishRecord:
    external_id: str
    status: PublishStatus
    source_task: str = ""
    goofish_product_id: str = ""
    xianyu_item_id: str = ""
    title: str = ""
    price_fen: int = 0
    error: str = ""
    updated_at: str = ""
