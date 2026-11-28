from pathlib import Path

import cv2
import numpy as np

from katao_xianyu.infrastructure.card_cropper import (
    OpenCvCardCropper,
    detect_and_crop_card,
)


def _synthetic_card_scene(width: int = 800, height: int = 1000) -> np.ndarray:
    """Gray background with a white card rectangle in the center + fake corner text."""
    img = np.full((height, width, 3), 40, dtype=np.uint8)
    # seller-ish banner at top
    cv2.rectangle(img, (0, 0), (width, 80), (20, 20, 180), -1)
    cv2.putText(
        img, "BAJIAO", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2
    )
    # card face
    x0, y0, x1, y1 = 180, 160, 620, 860
    cv2.rectangle(img, (x0, y0), (x1, y1), (240, 240, 240), -1)
    cv2.rectangle(img, (x0, y0), (x1, y1), (10, 10, 10), 4)
    cv2.putText(
        img, "CARD", (300, 520), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (30, 30, 30), 3
    )
    return img


def test_detect_and_crop_keeps_card_drops_banner():
    scene = _synthetic_card_scene()
    cropped = detect_and_crop_card(scene)
    ch, cw = cropped.shape[:2]
    assert ch > 400
    assert cw > 300
    # Cropped height should be smaller than full scene (banner removed)
    assert ch < scene.shape[0] * 0.95


def test_opencv_cropper_writes_cache(tmp_path: Path, monkeypatch):
    scene = _synthetic_card_scene()
    ok, buf = cv2.imencode(".jpg", scene)
    assert ok

    class _Resp:
        content = buf.tobytes()

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "katao_xianyu.infrastructure.card_cropper.requests.get",
        lambda *a, **k: _Resp(),
    )
    cropper = OpenCvCardCropper(tmp_path / "crops")
    path = cropper.crop_to_file(source_url="https://example.com/a.jpg", external_id="42")
    assert path.is_file()
    assert path.name == "42.jpg"
    # second call hits cache
    path2 = cropper.crop_to_file(source_url="https://example.com/a.jpg", external_id="42")
    assert path2 == path
