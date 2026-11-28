import json
from pathlib import Path

from katao_xianyu.infrastructure.live_json_source import LiveJsonWinSource


def test_live_json_enriches_nested_list_json(tmp_path: Path):
    results = tmp_path / "results" / "2026-11-01-DEMO-LIVE"
    results.mkdir(parents=True)
    (results / "live-summary.json").write_text(
        json.dumps(
            {
                "wins": [
                    {
                        "id": "42",
                        "title": "【拔脚代卖】不要用",
                        "final_price": "12.5",
                        "outcome": "won",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    nested = tmp_path / "runs" / "wt" / "worktree" / "results" / "demo"
    nested.mkdir(parents=True)
    (nested / "list.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "42",
                        "image": "https://images.cardhobby.com/x.jpg",
                        "identity": {
                            "brand": "Topps",
                            "player_query": "Demo Player",
                            "year_raw": "2025",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    source = LiveJsonWinSource(tmp_path / "results", tmp_path / "runs")
    wins = source.list_wins()
    assert len(wins) == 1
    assert wins[0].image_url.endswith("x.jpg")
    assert wins[0].identity.brand == "Topps"
    assert wins[0].identity.player_query == "Demo Player"
