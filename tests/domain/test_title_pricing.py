from katao_xianyu.domain.models import CardIdentity, WonCard
from katao_xianyu.domain.pricing import suggest_price_fen
from katao_xianyu.domain.title import build_content, build_title


def test_build_title_from_identity_not_auction_watermark():
    identity = CardIdentity(
        year="2023",
        year_raw="2022-23",
        brand="Panini",
        series="Chronicle",
        series_display="Chronicle",
        players=("gerard pique",),
        player_query="Gerard Pique",
        serial="39",
        print_run="50",
        parallel_phrases=("物料签",),
        signed=True,
        attribute_form="签字",
    )
    title = build_title(identity)
    assert "拔脚" not in title
    assert "腕龙" not in title
    assert "Panini" in title
    assert "Pique" in title
    assert len(title) <= 60


def test_build_content_includes_merchant_code():
    card = WonCard(
        external_id="153282293",
        source_task="demo-LIVE",
        auction_title="【腕龙代卖】不要用这个",
        cost_yuan=220.0,
        image_url="https://images.cardhobby.com/x.jpg",
        identity=CardIdentity(brand="Panini", player_query="Gerard Pique"),
    )
    content = build_content(card)
    assert "153282293" in content
    assert "腕龙" not in content
    assert "Gerard Pique" in content


def test_suggest_price_never_below_cost():
    assert suggest_price_fen(10000, markup_ratio=1.35) >= 10000
    assert suggest_price_fen(10000, markup_ratio=0.5) == 10000
