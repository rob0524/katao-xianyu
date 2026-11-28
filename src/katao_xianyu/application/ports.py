from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from katao_xianyu.domain.models import PublishRecord, WonCard


class WinSource(Protocol):
    def list_wins(self) -> list[WonCard]:
        """Return real auction wins enriched with image/identity when available."""

    def get_win(self, external_id: str) -> WonCard | None:
        ...


class ListingStateStore(Protocol):
    def get(self, external_id: str) -> PublishRecord | None:
        ...

    def upsert(self, record: PublishRecord) -> None:
        ...

    def list_records(self) -> list[PublishRecord]:
        ...

    def is_listed(self, external_id: str) -> bool:
        ...


class GoofishPort(Protocol):
    def get_authorize_list(self) -> Any:
        ...

    def list_categories(self, *, item_biz_type: int = 2, sp_biz_type: int | None = None) -> Any:
        ...

    def create_product(self, product_data: dict[str, Any]) -> Any:
        ...


class CardCropper(Protocol):
    def crop_to_file(self, *, source_url: str, external_id: str) -> Path:
        """Download source image, crop card face, write JPEG cache. Raise on failure."""


class ImageHost(Protocol):
    def is_configured(self) -> bool:
        ...

    def upload(self, *, object_key: str, file_path: Path, content_type: str = "image/jpeg") -> str:
        """Upload file and return a public HTTPS URL."""
