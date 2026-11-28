from katao_xianyu.application.build_draft import BuildDraft, PricingConfig
from katao_xianyu.application.publish_listing import (
    ChannelPropertyValue,
    ShopPublishConfig,
    draft_to_product_payload,
)
from katao_xianyu.domain.models import CardIdentity, WonCard


class _FakeWins:
    def __init__(self, card: WonCard) -> None:
        self._card = card

    def list_wins(self):
        return [self._card]

    def get_win(self, external_id: str):
        return self._card if external_id == self._card.external_id else None


def test_build_draft_rewrites_title():
    card = WonCard(
        external_id="1",
        source_task="t-LIVE",
        auction_title="【拔脚代卖】拍卖原标题",
        cost_yuan=100.0,
        image_url="https://images.cardhobby.com/a.jpg",
        identity=CardIdentity(
            year_raw="2025-26",
            brand="Topps",
            series_display="Chrome",
            player_query="Timo Werner",
            serial="46",
            print_run="50",
            parallel_phrases=("金折",),
            signed=True,
            attribute_form="签字",
        ),
    )
    draft = BuildDraft(_FakeWins(card), PricingConfig(markup_ratio=1.5)).from_card(card)
    assert "拔脚" not in draft.title
    assert "Topps" in draft.title
    assert draft.price_fen == 15000
    assert draft.source_image_url == "https://images.cardhobby.com/a.jpg"
    assert draft.image_urls == ()  # listing images only after crop+upload


def test_draft_to_product_payload():
    card = WonCard(
        external_id="99",
        source_task="t",
        auction_title="x",
        cost_yuan=10,
        image_url="https://images.cardhobby.com/a.jpg",
        identity=CardIdentity(brand="Topps", player_query="A"),
    )
    draft = BuildDraft(_FakeWins(card)).from_card(card)
    draft = draft.with_overrides(image_urls=("https://cdn.example.com/crops/99.jpg",))
    shop = ShopPublishConfig(
        user_name="shop",
        province=110000,
        city=110100,
        district=110101,
        express_fee_fen=0,
        sp_biz_type=28,
        channel_cat_id="cat-1",
        channel_pv=(
            ChannelPropertyValue(
                property_id="3b9f06b2bccead76",
                property_name="成色",
                value_id="38fb2f464f74f87b14cfee7282107eb6",
                value_name="品相完好无瑕疵",
            ),
        ),
    )
    payload = draft_to_product_payload(draft, shop, title_prefix="[测试]")
    assert payload["item_biz_type"] == 2
    assert payload["outer_id"] == "99"
    assert payload["publish_shop"][0]["title"].startswith("[测试]")
    assert payload["publish_shop"][0]["images"] == [
        "https://cdn.example.com/crops/99.jpg"
    ]
    assert "cardhobby.com" not in payload["publish_shop"][0]["images"][0]
    assert payload["channel_pv"][0]["value_name"] == "品相完好无瑕疵"
