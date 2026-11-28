from katao_xianyu.application.publish_listing import PublishListing, ShopPublishConfig
from katao_xianyu.domain.models import ListingDraft, PublishRecord, PublishStatus


class _FakeState:
    def __init__(self) -> None:
        self.records: dict[str, PublishRecord] = {}

    def get(self, external_id: str):
        return self.records.get(external_id)

    def upsert(self, record: PublishRecord) -> None:
        self.records[record.external_id] = record

    def list_records(self):
        return list(self.records.values())

    def is_listed(self, external_id: str) -> bool:
        r = self.records.get(external_id)
        return bool(r and r.status == PublishStatus.LISTED)


class _FakeGoofish:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get_authorize_list(self):
        return {}

    def list_categories(self, **kwargs):
        return {}

    def create_product(self, product_data):
        self.calls.append(product_data)
        return self.response


def _draft() -> ListingDraft:
    return ListingDraft(
        external_id="1",
        source_task="t",
        title="Hello",
        content="desc here ok",
        image_urls=("https://images.cardhobby.com/a.jpg",),
        price_fen=1000,
        cost_fen=800,
        auction_title="auction",
        outer_id="1",
    )


def _shop() -> ShopPublishConfig:
    return ShopPublishConfig(
        user_name="shop",
        province=1,
        city=1,
        district=1,
        express_fee_fen=0,
        sp_biz_type=28,
        channel_cat_id="cat",
    )


def test_publish_success_requires_product_id():
    state = _FakeState()
    gf = _FakeGoofish({"code": 0, "msg": "OK", "data": {"product_id": "pid-9"}})
    result = PublishListing(gf, state, _shop()).execute(_draft())
    assert result.ok
    assert result.record.status == PublishStatus.LISTED
    assert result.record.goofish_product_id == "pid-9"


def test_publish_stringish_error_dict_not_listed():
    state = _FakeState()
    gf = _FakeGoofish({"code": 500, "msg": "fail"})
    result = PublishListing(gf, state, _shop()).execute(_draft())
    assert not result.ok
    assert result.record.status == PublishStatus.PUBLISH_FAILED


def test_publish_code_ok_without_id_fails():
    state = _FakeState()
    gf = _FakeGoofish({"code": 0, "msg": "OK", "data": {}})
    result = PublishListing(gf, state, _shop()).execute(_draft())
    assert not result.ok
    assert result.record.status == PublishStatus.PUBLISH_FAILED
