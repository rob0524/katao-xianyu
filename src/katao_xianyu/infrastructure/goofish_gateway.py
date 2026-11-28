from __future__ import annotations

import json
from typing import Any


def normalize_goofish_response(raw: Any) -> dict[str, Any]:
    """SDK often returns a JSON string body; normalize to a dict for use cases."""
    if raw is None:
        return {"code": -1, "msg": "empty response", "data": None}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {"code": -1, "msg": "empty response", "data": None}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"code": -1, "msg": text, "data": None}
        if isinstance(parsed, dict):
            return parsed
        return {"code": 0, "msg": "OK", "data": parsed}
    return {"code": -1, "msg": str(raw), "data": None}


class GoofishGateway:
    """Thin adapter over community goofish-api SDK. No business rules."""

    def __init__(self, app_key: str, app_secret: str, *, debug: bool = False) -> None:
        if not app_key or not app_secret:
            raise ValueError("GOOFISH_APP_KEY / GOOFISH_APP_SECRET required")
        # Lazy import so list-wins/draft CLI work without SDK import side effects
        from goofish_api import GoofishClient

        # IMPORTANT: community SDK signature is
        #   GoofishClient(app_key, app_secret, debug=False)
        # but BaseClient is (app_key, app_secret, seller_id=None, debug=False).
        # Passing debug=True becomes seller_id=True → API error
        #   strconv.ParseInt: parsing "True"
        # Never pass the third positional/kw debug through.
        self._debug = debug
        self._client = GoofishClient(app_key, app_secret)

    def get_authorize_list(self) -> Any:
        return normalize_goofish_response(self._client.user.get_authorize_list())

    def list_categories(
        self, *, item_biz_type: int = 2, sp_biz_type: int | None = None
    ) -> Any:
        payload: dict[str, Any] = {"item_biz_type": item_biz_type}
        if sp_biz_type is not None and sp_biz_type != 0:
            payload["sp_biz_type"] = sp_biz_type
        good = self._client.good
        if hasattr(good, "get_product_category_list"):
            raw = good.get_product_category_list(**payload)
        elif hasattr(good, "get_category_list"):
            raw = good.get_category_list(payload)
        else:
            raise AttributeError(
                "goofish_api client.good has no category list method; "
                f"available: {[n for n in dir(good) if not n.startswith('_')]}"
            )
        return normalize_goofish_response(raw)

    def create_product(self, product_data: dict[str, Any]) -> Any:
        raw = self._client.good.create_product(product_data=product_data)
        return normalize_goofish_response(raw)

    def edit_product(self, product_data: dict[str, Any]) -> Any:
        raw = self._client.good.product_edit(product_data=product_data)
        return normalize_goofish_response(raw)
