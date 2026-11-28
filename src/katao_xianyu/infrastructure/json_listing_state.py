from __future__ import annotations

import json
from pathlib import Path

from katao_xianyu.domain.models import PublishRecord, PublishStatus


class JsonListingStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def _read_all(self) -> dict[str, dict]:
        if not self._path.is_file():
            return {}
        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        records = data.get("records")
        if isinstance(records, dict):
            return records
        return {}

    def _write_all(self, records: dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"records": records}
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp.replace(self._path)

    @staticmethod
    def _from_dict(external_id: str, data: dict) -> PublishRecord:
        status_raw = data.get("status", PublishStatus.PENDING.value)
        try:
            status = PublishStatus(status_raw)
        except ValueError:
            status = PublishStatus.PENDING
        return PublishRecord(
            external_id=external_id,
            status=status,
            source_task=str(data.get("source_task") or ""),
            goofish_product_id=str(data.get("goofish_product_id") or ""),
            xianyu_item_id=str(data.get("xianyu_item_id") or ""),
            title=str(data.get("title") or ""),
            price_fen=int(data.get("price_fen") or 0),
            error=str(data.get("error") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )

    @staticmethod
    def _to_dict(record: PublishRecord) -> dict:
        return {
            "status": record.status.value,
            "source_task": record.source_task,
            "goofish_product_id": record.goofish_product_id,
            "xianyu_item_id": record.xianyu_item_id,
            "title": record.title,
            "price_fen": record.price_fen,
            "error": record.error,
            "updated_at": record.updated_at,
        }

    def get(self, external_id: str) -> PublishRecord | None:
        raw = self._read_all().get(external_id)
        if raw is None:
            return None
        return self._from_dict(external_id, raw)

    def upsert(self, record: PublishRecord) -> None:
        all_records = self._read_all()
        all_records[record.external_id] = self._to_dict(record)
        self._write_all(all_records)

    def list_records(self) -> list[PublishRecord]:
        return [
            self._from_dict(eid, data) for eid, data in sorted(self._read_all().items())
        ]

    def is_listed(self, external_id: str) -> bool:
        record = self.get(external_id)
        return bool(record and record.status == PublishStatus.LISTED)
