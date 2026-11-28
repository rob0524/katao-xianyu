from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from katao_xianyu.application.ports import GoofishPort


@dataclass(frozen=True)
class ProbeResult:
    authorize_list: Any
    categories: Any | None = None


class ProbeShop:
    """Phase 0 connectivity: authorized shops + optional category probe."""

    def __init__(self, goofish: GoofishPort) -> None:
        self._goofish = goofish

    def execute(
        self,
        *,
        list_categories: bool = False,
        sp_biz_type: int | None = None,
    ) -> ProbeResult:
        auth = self._goofish.get_authorize_list()
        cats = None
        if list_categories:
            cats = self._goofish.list_categories(
                item_biz_type=2,
                sp_biz_type=sp_biz_type,
            )
        return ProbeResult(authorize_list=auth, categories=cats)
