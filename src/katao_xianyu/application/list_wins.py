from __future__ import annotations

from dataclasses import dataclass

from katao_xianyu.application.ports import ListingStateStore, WinSource
from katao_xianyu.domain.models import PublishStatus, WonCard


@dataclass(frozen=True)
class PendingWin:
    card: WonCard
    already_listed: bool
    status: PublishStatus | None


class ListPendingWins:
    def __init__(self, wins: WinSource, state: ListingStateStore) -> None:
        self._wins = wins
        self._state = state

    def execute(self, *, include_listed: bool = False) -> list[PendingWin]:
        out: list[PendingWin] = []
        for card in self._wins.list_wins():
            record = self._state.get(card.external_id)
            already = bool(record and record.status == PublishStatus.LISTED)
            if already and not include_listed:
                continue
            out.append(
                PendingWin(
                    card=card,
                    already_listed=already,
                    status=record.status if record else None,
                )
            )
        return out
