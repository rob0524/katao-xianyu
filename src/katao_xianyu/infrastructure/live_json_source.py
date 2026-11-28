from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from katao_xianyu.domain.models import CardIdentity, WonCard


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _as_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _iter_won_items(summary: dict[str, Any]) -> list[dict[str, Any]]:
    wins = summary.get("wins")
    if isinstance(wins, list) and wins:
        return [w for w in wins if isinstance(w, dict)]
    items = summary.get("items") or []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("outcome") == "won":
            out.append(item)
    return out


class LiveJsonWinSource:
    """Read LIVE settlement JSON and enrich from scan list.json by id."""

    def __init__(self, results_dir: Path, runs_dir: Path) -> None:
        self._results_dir = results_dir
        self._runs_dir = runs_dir
        self._list_index: dict[str, dict[str, Any]] | None = None

    def _build_list_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        if not self._runs_dir.is_dir():
            return index
        # Nested worktrees keep list.json deeper than runs/<task>/list.json
        for list_path in sorted(self._runs_dir.rglob("list.json")):
            try:
                data = _load_json(list_path)
            except (OSError, json.JSONDecodeError):
                continue
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "")
                if not item_id:
                    continue
                # Prefer entries that already have image + identity
                prev = index.get(item_id)
                if prev is None:
                    index[item_id] = item
                    continue
                prev_score = int(bool(prev.get("image"))) + int(
                    isinstance(prev.get("identity"), dict)
                )
                new_score = int(bool(item.get("image"))) + int(
                    isinstance(item.get("identity"), dict)
                )
                if new_score >= prev_score:
                    index[item_id] = item
        return index

    def _enrichment(self, external_id: str) -> dict[str, Any]:
        if self._list_index is None:
            self._list_index = self._build_list_index()
        return self._list_index.get(external_id, {})

    def _to_won_card(self, raw: dict[str, Any], source_task: str) -> WonCard | None:
        external_id = str(raw.get("id") or "").strip()
        if not external_id:
            return None
        # Prefer explicit won; wins[] entries may omit outcome
        outcome = raw.get("outcome")
        if outcome is not None and outcome != "won":
            return None

        enrich = self._enrichment(external_id)
        image = str(raw.get("image") or enrich.get("image") or "")
        identity_data = enrich.get("identity") if isinstance(enrich.get("identity"), dict) else {}
        if not identity_data and isinstance(raw.get("identity"), dict):
            identity_data = raw["identity"]

        cost = _as_float(raw.get("final_price"))
        if cost <= 0:
            cost = _as_float(raw.get("ceiling"))

        return WonCard(
            external_id=external_id,
            source_task=source_task,
            auction_title=str(raw.get("title") or enrich.get("title") or ""),
            cost_yuan=cost,
            image_url=image,
            identity=CardIdentity.from_dict(identity_data),
            auction_link=str(raw.get("link") or enrich.get("link") or ""),
            payment_due=str(raw.get("payment_due") or ""),
            final_price_raw=str(raw.get("final_price") or ""),
        )

    def list_wins(self) -> list[WonCard]:
        if not self._results_dir.is_dir():
            return []

        by_id: dict[str, WonCard] = {}
        for summary_path in sorted(self._results_dir.rglob("live-summary.json")):
            parent_name = summary_path.parent.name
            if "LIVE" not in parent_name.upper():
                continue
            source_task = parent_name
            try:
                summary = _load_json(summary_path)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(summary, dict):
                continue
            for raw in _iter_won_items(summary):
                card = self._to_won_card(raw, source_task)
                if card is None:
                    continue
                # Later files (sorted paths) overwrite duplicate ids
                by_id[card.external_id] = card

        return sorted(by_id.values(), key=lambda c: (c.source_task, c.external_id))

    def get_win(self, external_id: str) -> WonCard | None:
        for card in self.list_wins():
            if card.external_id == external_id:
                return card
        return None
