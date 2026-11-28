from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from katao_xianyu.application.ports import CardCropper, ImageHost, WinSource


class ImagePrepareError(ValueError):
    """Crop or host failed; callers must not fall back to watermarked source URL."""


@dataclass(frozen=True)
class PreparedListingImage:
    external_id: str
    source_url: str
    local_path: Path
    public_url: str | None


class PrepareListingImage:
    """Crop CardHobby image to card face; optionally upload for a public URL."""

    def __init__(
        self,
        wins: WinSource,
        cropper: CardCropper,
        host: ImageHost,
        *,
        key_prefix: str = "katao-xianyu/crops/",
    ) -> None:
        self._wins = wins
        self._cropper = cropper
        self._host = host
        self._key_prefix = key_prefix.rstrip("/") + "/"

    def execute(
        self,
        external_id: str,
        *,
        require_public_url: bool = False,
        source_url: str | None = None,
    ) -> PreparedListingImage:
        url = (source_url or "").strip()
        if not url:
            card = self._wins.get_win(external_id)
            if card is None:
                raise KeyError(f"win not found: {external_id}")
            url = card.source_image_url.strip()
        if not url:
            raise ImagePrepareError(f"no source image for {external_id}")

        try:
            local_path = self._cropper.crop_to_file(source_url=url, external_id=external_id)
        except Exception as exc:  # noqa: BLE001 — normalize for CLI/publish
            raise ImagePrepareError(f"card crop failed for {external_id}: {exc}") from exc

        public_url: str | None = None
        if require_public_url or self._host.is_configured():
            if not self._host.is_configured():
                raise ImagePrepareError(
                    "image host (OSS) is not configured; set IMAGE_OSS_* in .env. "
                    "Cannot publish CardHobby source images with seller watermarks."
                )
            object_key = f"{self._key_prefix}{external_id}.jpg"
            try:
                public_url = self._host.upload(
                    object_key=object_key,
                    file_path=local_path,
                    content_type="image/jpeg",
                )
            except Exception as exc:  # noqa: BLE001
                raise ImagePrepareError(
                    f"image upload failed for {external_id}: {exc}"
                ) from exc

        if require_public_url and not public_url:
            raise ImagePrepareError(f"missing public URL after prepare for {external_id}")

        return PreparedListingImage(
            external_id=external_id,
            source_url=url,
            local_path=local_path,
            public_url=public_url,
        )
