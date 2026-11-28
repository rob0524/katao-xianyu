from pathlib import Path

from katao_xianyu.domain.models import PublishRecord, PublishStatus
from katao_xianyu.infrastructure.json_listing_state import JsonListingStateStore


def test_json_listing_state_roundtrip(tmp_path: Path):
    path = tmp_path / "listing-state.json"
    store = JsonListingStateStore(path)
    store.upsert(
        PublishRecord(
            external_id="1",
            status=PublishStatus.LISTED,
            goofish_product_id="g1",
            title="t",
            price_fen=100,
        )
    )
    assert store.is_listed("1")
    got = store.get("1")
    assert got is not None
    assert got.goofish_product_id == "g1"
    assert store.list_records()[0].external_id == "1"
