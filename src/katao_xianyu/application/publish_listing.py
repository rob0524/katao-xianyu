from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from katao_xianyu.application.ports import GoofishPort, ListingStateStore
from katao_xianyu.domain.models import ListingDraft, PublishRecord, PublishStatus


@dataclass(frozen=True)
class ChannelPropertyValue:
    """Goofish channel_pv item (e.g. 成色=品相完好无瑕疵)."""

    property_id: str
    property_name: str
    value_id: str
    value_name: str

    def to_api(self) -> dict[str, str]:
        return {
            "property_id": self.property_id,
            "property_name": self.property_name,
            "value_id": self.value_id,
            "value_name": self.value_name,
        }


@dataclass(frozen=True)
class ShopPublishConfig:
    user_name: str
    province: int
    city: int
    district: int
    express_fee_fen: int
    sp_biz_type: int
    channel_cat_id: str
    item_biz_type: int = 2
    stock: int = 1
    channel_pv: tuple[ChannelPropertyValue, ...] = ()


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    record: PublishRecord
    raw_response: Any = None


def draft_to_product_payload(
    draft: ListingDraft,
    shop: ShopPublishConfig,
    *,
    title_prefix: str = "",
) -> dict[str, Any]:
    title = f"{title_prefix}{draft.title}" if title_prefix else draft.title
    if not draft.image_urls:
        raise ValueError("draft has no image_urls; Goofish requires public image URLs")
    if not shop.channel_cat_id:
        raise ValueError("GOOFISH_CHANNEL_CAT_ID is empty; run probe categories first")
    if not shop.user_name:
        raise ValueError("GOOFISH_SHOP_USER is empty")

    payload: dict[str, Any] = {
        "item_biz_type": shop.item_biz_type,
        "sp_biz_type": shop.sp_biz_type,
        "channel_cat_id": shop.channel_cat_id,
        "price": draft.price_fen,
        "express_fee": shop.express_fee_fen,
        "stock": shop.stock,
        "outer_id": draft.outer_id or draft.external_id,
        "stuff_status": draft.stuff_status,
        "publish_shop": [
            {
                "user_name": shop.user_name,
                "province": shop.province,
                "city": shop.city,
                "district": shop.district,
                "title": title,
                "content": draft.content,
                "images": list(draft.image_urls),
            }
        ],
    }
    if shop.channel_pv:
        payload["channel_pv"] = [item.to_api() for item in shop.channel_pv]
    return payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _extract_product_id(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, dict):
        data = response.get("data") if "data" in response else response
        if isinstance(data, dict):
            for key in ("product_id", "id", "item_id", "productId"):
                if data.get(key) is not None:
                    return str(data[key])
        if response.get("product_id") is not None:
            return str(response["product_id"])
    return ""


class PublishListing:
    """Create product via Goofish. Caller controls whether to later publish/shelf."""

    def __init__(
        self,
        goofish: GoofishPort,
        state: ListingStateStore,
        shop: ShopPublishConfig,
    ) -> None:
        self._goofish = goofish
        self._state = state
        self._shop = shop

    def execute(
        self,
        draft: ListingDraft,
        *,
        title_prefix: str = "",
        force: bool = False,
    ) -> PublishResult:
        if not force and self._state.is_listed(draft.external_id):
            existing = self._state.get(draft.external_id)
            if existing is None:
                raise RuntimeError(f"listed flag set but record missing: {draft.external_id}")
            return PublishResult(ok=False, record=existing, raw_response=None)

        payload = draft_to_product_payload(
            draft, self._shop, title_prefix=title_prefix
        )
        try:
            raw = self._goofish.create_product(payload)
        except Exception as exc:  # noqa: BLE001 — surface to state + CLI
            record = PublishRecord(
                external_id=draft.external_id,
                status=PublishStatus.PUBLISH_FAILED,
                source_task=draft.source_task,
                title=draft.title,
                price_fen=draft.price_fen,
                error=str(exc),
                updated_at=_now_iso(),
            )
            self._state.upsert(record)
            return PublishResult(ok=False, record=record, raw_response=None)

        if not isinstance(raw, dict):
            record = PublishRecord(
                external_id=draft.external_id,
                status=PublishStatus.PUBLISH_FAILED,
                source_task=draft.source_task,
                title=draft.title,
                price_fen=draft.price_fen,
                error=f"unexpected response type: {type(raw).__name__}",
                updated_at=_now_iso(),
            )
            self._state.upsert(record)
            return PublishResult(ok=False, record=record, raw_response=raw)

        msg = str(raw.get("msg") or "")
        code_ok = raw.get("code") in (0, "0")
        product_id = _extract_product_id(raw)
        ok = code_ok and bool(product_id)

        if ok:
            record = PublishRecord(
                external_id=draft.external_id,
                status=PublishStatus.LISTED,
                source_task=draft.source_task,
                goofish_product_id=product_id,
                title=draft.title,
                price_fen=draft.price_fen,
                error="",
                updated_at=_now_iso(),
            )
        else:
            error = msg or str(raw)
            if code_ok and not product_id:
                error = "success code but missing product id in response"
            record = PublishRecord(
                external_id=draft.external_id,
                status=PublishStatus.PUBLISH_FAILED,
                source_task=draft.source_task,
                title=draft.title,
                price_fen=draft.price_fen,
                error=error,
                updated_at=_now_iso(),
            )
        self._state.upsert(record)
        return PublishResult(ok=ok, record=record, raw_response=raw)
