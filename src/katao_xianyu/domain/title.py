from __future__ import annotations

from katao_xianyu.domain.models import CardIdentity, WonCard

# 闲管家标题上限：按字符计，中文也算 1；文档写一个中文按 2，保守截到 30 汉字量级
_TITLE_MAX_CHARS = 60


def _player_label(identity: CardIdentity) -> str:
    if identity.player_query:
        return identity.player_query.strip()
    if identity.players:
        return " ".join(identity.players)
    return ""


def _parallel_label(identity: CardIdentity) -> str:
    if identity.parallel_phrases:
        return " ".join(identity.parallel_phrases)
    if identity.parallel:
        return " ".join(identity.parallel)
    return ""


def _serial_label(identity: CardIdentity) -> str:
    serial = identity.serial.strip()
    if not serial:
        return ""
    if identity.print_run:
        return f"{serial}/{identity.print_run}"
    if "/" in serial:
        return serial
    return f"/{serial}编" if serial.isdigit() else serial


def _clip(text: str, max_chars: int = _TITLE_MAX_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def build_title(identity: CardIdentity, *, fallback: str = "球星卡") -> str:
    """Build a clean Xianyu title from structured identity — never auction watermark."""
    year = identity.year_raw or identity.year
    series = identity.series_display or identity.series
    parts = [
        year,
        identity.brand,
        series,
        _player_label(identity),
        _parallel_label(identity),
        _serial_label(identity),
    ]
    if identity.signed or identity.attribute_form:
        parts.append(identity.attribute_form or "签字")
    if identity.grading:
        parts.append(str(identity.grading))

    title = " ".join(p for p in parts if p)
    return _clip(title) if title else _clip(fallback)


def build_content(card: WonCard) -> str:
    """Plain-text description for Goofish (no HTML)."""
    identity = card.identity
    lines: list[str] = [
        "【商品说明】",
        f"年份：{identity.year_raw or identity.year or '—'}",
        f"品牌：{identity.brand or '—'}",
        f"系列：{identity.series_display or identity.series or '—'}",
        f"球员：{_player_label(identity) or '—'}",
    ]
    if identity.teams:
        lines.append(f"球队：{' / '.join(identity.teams)}")
    serial = _serial_label(identity)
    if serial:
        lines.append(f"编号：{serial}")
    parallel = _parallel_label(identity)
    if parallel:
        lines.append(f"平行：{parallel}")
    if identity.signed or identity.attribute_form:
        lines.append(f"特色：{identity.attribute_form or '签字'}")
    if identity.grading:
        lines.append(f"评级：{identity.grading}")

    lines.extend(
        [
            "",
            "【品相】",
            "如图所示，细节请看图。有疑问先沟通再下单。",
            "",
            "【发货】",
            "付款后尽快发出，支持闲鱼物流。",
            "",
            f"商家编码：{card.external_id}",
        ]
    )
    return "\n".join(lines)
