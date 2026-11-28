from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import requests

log = logging.getLogger(__name__)


class CardCropError(RuntimeError):
    pass


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Return corners in order: tl, tr, br, bl."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _warp_card(image: np.ndarray, approx: np.ndarray) -> np.ndarray:
    pts = approx.reshape(4, 2).astype("float32")
    rect = _order_corners(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b), 1)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b), 1)
    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_w, max_h))


def _axis_aligned_crop(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
    x, y, w, h = cv2.boundingRect(contour)
    h_img, w_img = image.shape[:2]
    pad = 2
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w_img, x + w + pad)
    y1 = min(h_img, y + h + pad)
    return image[y0:y1, x0:x1]


def detect_and_crop_card(image_bgr: np.ndarray) -> np.ndarray:
    """Detect the dominant card rectangle and return a cropped BGR image."""
    if image_bgr is None or image_bgr.size == 0:
        raise CardCropError("empty image")

    h, w = image_bgr.shape[:2]
    area_img = float(h * w)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise CardCropError("no contours found")

    center = np.array([w / 2.0, h / 2.0])
    candidates: list[tuple[float, np.ndarray, bool]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        ratio = area / area_img
        if ratio < 0.15 or ratio > 0.95:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        x, y, bw, bh = cv2.boundingRect(contour)
        if bw < 1 or bh < 1:
            continue
        aspect = bw / float(bh)
        # Trading cards ~2.5x3.5 → ~0.71; allow graded slabs / slight tilt
        if aspect < 0.45 or aspect > 1.35:
            continue
        m = cv2.moments(contour)
        if m["m00"] == 0:
            continue
        cx = m["m10"] / m["m00"]
        cy = m["m01"] / m["m00"]
        dist = np.linalg.norm(np.array([cx, cy]) - center) / max(w, h)
        # Prefer larger, more centered cards
        score = ratio - 0.35 * dist
        is_quad = len(approx) == 4 and cv2.isContourConvex(approx)
        candidates.append((score, contour if not is_quad else approx, is_quad))

    if not candidates:
        # Fallback: largest contour in area band without aspect filter
        fallback = []
        for contour in contours:
            area = cv2.contourArea(contour)
            ratio = area / area_img
            if 0.20 <= ratio <= 0.92:
                fallback.append((area, contour))
        if not fallback:
            raise CardCropError("no card-like contour in area band 15%–95%")
        fallback.sort(key=lambda t: t[0], reverse=True)
        cropped = _axis_aligned_crop(image_bgr, fallback[0][1])
    else:
        candidates.sort(key=lambda t: t[0], reverse=True)
        _score, shape, is_quad = candidates[0]
        if is_quad:
            cropped = _warp_card(image_bgr, shape)
        else:
            cropped = _axis_aligned_crop(image_bgr, shape)

    if cropped.size == 0 or min(cropped.shape[:2]) < 32:
        raise CardCropError("cropped region too small")
    return cropped


def download_image(url: str, *, timeout: float = 60.0) -> np.ndarray:
    headers = {
        "User-Agent": "katao-xianyu/0.1 (+card-crop)",
        "Referer": "https://www.cardhobby.com.cn/",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    arr = np.frombuffer(resp.content, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise CardCropError("failed to decode downloaded image")
    return image


class OpenCvCardCropper:
    """Download + OpenCV card-face crop with local JPEG cache under crops_dir."""

    def __init__(self, crops_dir: Path, *, force: bool = False) -> None:
        self._crops_dir = crops_dir
        self._force = force

    def crop_to_file(self, *, source_url: str, external_id: str) -> Path:
        self._crops_dir.mkdir(parents=True, exist_ok=True)
        out = self._crops_dir / f"{external_id}.jpg"
        if out.is_file() and not self._force and out.stat().st_size > 0:
            return out

        image = download_image(source_url)
        cropped = detect_and_crop_card(image)
        ok = cv2.imwrite(str(out), cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok or not out.is_file():
            raise CardCropError(f"failed to write crop file: {out}")
        log.info("cropped card %s → %s", external_id, out)
        return out
