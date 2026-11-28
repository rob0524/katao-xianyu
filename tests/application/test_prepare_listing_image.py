from pathlib import Path

import pytest

from katao_xianyu.application.prepare_listing_image import (
    ImagePrepareError,
    PrepareListingImage,
)
from katao_xianyu.domain.models import CardIdentity, WonCard


class _FakeWins:
    def __init__(self, card: WonCard) -> None:
        self._card = card

    def list_wins(self):
        return [self._card]

    def get_win(self, external_id: str):
        return self._card if external_id == self._card.external_id else None


class _FakeCropper:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.calls = []

    def crop_to_file(self, *, source_url: str, external_id: str) -> Path:
        self.calls.append((source_url, external_id))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"jpeg")
        return self.path


class _FakeHost:
    def __init__(self, configured: bool = True) -> None:
        self.configured = configured
        self.uploads = []

    def is_configured(self) -> bool:
        return self.configured

    def upload(self, *, object_key: str, file_path: Path, content_type: str = "image/jpeg") -> str:
        self.uploads.append(object_key)
        return f"https://cdn.example.com/{object_key}"


def _card() -> WonCard:
    return WonCard(
        external_id="1",
        source_task="t",
        auction_title="x",
        cost_yuan=10,
        image_url="https://images.cardhobby.com/a.jpg",
        identity=CardIdentity(),
    )


def test_prepare_local_only_without_host(tmp_path: Path):
    crop_path = tmp_path / "1.jpg"
    prep = PrepareListingImage(_FakeWins(_card()), _FakeCropper(crop_path), _FakeHost(False))
    result = prep.execute("1", require_public_url=False)
    assert result.local_path == crop_path
    assert result.public_url is None


def test_prepare_require_public_without_host_fails(tmp_path: Path):
    prep = PrepareListingImage(
        _FakeWins(_card()), _FakeCropper(tmp_path / "1.jpg"), _FakeHost(False)
    )
    with pytest.raises(ImagePrepareError, match="image host"):
        prep.execute("1", require_public_url=True)


def test_prepare_uploads_when_configured(tmp_path: Path):
    host = _FakeHost(True)
    prep = PrepareListingImage(
        _FakeWins(_card()), _FakeCropper(tmp_path / "1.jpg"), host
    )
    result = prep.execute("1", require_public_url=True)
    assert result.public_url.startswith("https://cdn.example.com/")
    assert "cardhobby.com" not in result.public_url
    assert host.uploads
