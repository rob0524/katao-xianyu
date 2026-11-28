from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from katao_xianyu.application.build_draft import BuildDraft
from katao_xianyu.application.list_wins import ListPendingWins
from katao_xianyu.application.prepare_listing_image import (
    ImagePrepareError,
    PrepareListingImage,
)
from katao_xianyu.application.probe_shop import ProbeShop
from katao_xianyu.application.publish_listing import PublishListing
from katao_xianyu.infrastructure.card_cropper import OpenCvCardCropper
from katao_xianyu.infrastructure.json_listing_state import JsonListingStateStore
from katao_xianyu.infrastructure.live_json_source import LiveJsonWinSource
from katao_xianyu.infrastructure.oss_image_host import build_image_host
from katao_xianyu.infrastructure.settings import Settings, load_settings


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _compose(settings: Settings) -> tuple[LiveJsonWinSource, JsonListingStateStore]:
    wins = LiveJsonWinSource(settings.results_dir, settings.runs_dir)
    state = JsonListingStateStore(settings.listing_state_path)
    return wins, state


def _compose_image_prep(
    settings: Settings, *, force_crop: bool = False
) -> tuple[LiveJsonWinSource, PrepareListingImage]:
    wins = LiveJsonWinSource(settings.results_dir, settings.runs_dir)
    cropper = OpenCvCardCropper(settings.crops_dir, force=force_crop)
    host = build_image_host(settings.image_oss)
    preparer = PrepareListingImage(
        wins,
        cropper,
        host,
        key_prefix=settings.image_oss_key_prefix,
    )
    return wins, preparer


def _require_goofish(settings: Settings):
    if not settings.goofish_ready:
        raise SystemExit(
            "Missing GOOFISH_APP_KEY / GOOFISH_APP_SECRET. Copy .env.example → .env"
        )
    from katao_xianyu.infrastructure.goofish_gateway import GoofishGateway

    return GoofishGateway(
        settings.goofish_app_key,
        settings.goofish_app_secret,
        debug=settings.goofish_debug,
    )


def cmd_probe(args: argparse.Namespace, settings: Settings) -> int:
    gateway = _require_goofish(settings)
    result = ProbeShop(gateway).execute(
        list_categories=args.categories,
        sp_biz_type=args.sp_biz_type or (settings.shop.sp_biz_type or None),
    )
    _print_json(
        {
            "authorize_list": result.authorize_list,
            "categories": result.categories,
        }
    )
    return 0


def cmd_list_wins(args: argparse.Namespace, settings: Settings) -> int:
    wins, state = _compose(settings)
    rows = ListPendingWins(wins, state).execute(include_listed=args.include_listed)
    payload = []
    for row in rows:
        card = row.card
        payload.append(
            {
                "external_id": card.external_id,
                "source_task": card.source_task,
                "cost_yuan": card.cost_yuan,
                "source_image_url": card.source_image_url,
                "auction_title": card.auction_title,
                "already_listed": row.already_listed,
                "status": row.status.value if row.status else None,
                "identity": {
                    "year": card.identity.year_raw or card.identity.year,
                    "brand": card.identity.brand,
                    "series": card.identity.series_display or card.identity.series,
                    "player": card.identity.player_query or list(card.identity.players),
                },
            }
        )
    _print_json({"count": len(payload), "wins": payload})
    return 0


def cmd_draft(args: argparse.Namespace, settings: Settings) -> int:
    wins, _state = _compose(settings)
    draft = BuildDraft(wins, settings.pricing).execute(args.id)
    _print_json(
        {
            "external_id": draft.external_id,
            "source_task": draft.source_task,
            "auction_title_ref_only": draft.auction_title,
            "title": draft.title,
            "content": draft.content,
            "source_image_url": draft.source_image_url,
            "image_urls": list(draft.image_urls),
            "note": "image_urls empty until prepare-image / publish crops card face",
            "cost_fen": draft.cost_fen,
            "price_fen": draft.price_fen,
            "price_yuan": draft.price_fen / 100,
            "stuff_status": draft.stuff_status,
            "outer_id": draft.outer_id,
        }
    )
    return 0


def cmd_prepare_image(args: argparse.Namespace, settings: Settings) -> int:
    _wins, preparer = _compose_image_prep(settings, force_crop=args.force)
    require_public = bool(args.upload)
    if args.upload and not settings.image_host_ready:
        raise SystemExit(
            "IMAGE_OSS_* not configured; prepare-image without --upload still works locally"
        )
    prepared = preparer.execute(
        args.id,
        require_public_url=require_public,
    )
    _print_json(
        {
            "external_id": prepared.external_id,
            "source_url": prepared.source_url,
            "local_path": str(prepared.local_path),
            "public_url": prepared.public_url,
            "uploaded": bool(prepared.public_url),
            "note": (
                "Open local_path to verify crop (seller watermark around edges should be gone). "
                "Center-of-card watermarks are not removed."
            ),
        }
    )
    return 0


def cmd_create_unpublished(args: argparse.Namespace, settings: Settings) -> int:
    """Create product using cropped public image URL only (never raw CardHobby)."""
    wins, state = _compose(settings)
    _wins, preparer = _compose_image_prep(settings, force_crop=args.force_crop)
    # Prepare first so missing OSS fails before Goofish SDK init (SDK prints keys).
    prepared = preparer.execute(args.id, require_public_url=True)
    assert prepared.public_url
    gateway = _require_goofish(settings)
    builder = BuildDraft(wins, settings.pricing)
    draft = builder.execute(args.id)
    draft = draft.with_overrides(image_urls=(prepared.public_url,))

    if args.title:
        draft = draft.with_overrides(title=args.title)
    if args.price_yuan is not None:
        draft = draft.with_overrides(price_fen=int(round(args.price_yuan * 100)))

    prefix = args.title_prefix if args.title_prefix is not None else "[测试]"
    publisher = PublishListing(gateway, state, settings.shop)
    result = publisher.execute(draft, title_prefix=prefix, force=args.force)
    _print_json(
        {
            "ok": result.ok,
            "record": {
                "external_id": result.record.external_id,
                "status": result.record.status.value,
                "goofish_product_id": result.record.goofish_product_id,
                "error": result.record.error,
                "title": result.record.title,
                "price_fen": result.record.price_fen,
            },
            "listing_image_url": prepared.public_url,
            "crop_local_path": str(prepared.local_path),
            "raw_response": result.raw_response,
            "note": "Uses create_product with cropped card-face image only.",
        }
    )
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="katao-xianyu",
        description="CardHobby wins → Xianyu via Goofish (layered CLI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="Check authorized shops (Phase 0)")
    probe.add_argument(
        "--categories",
        action="store_true",
        help="Also list product categories for ordinary goods",
    )
    probe.add_argument(
        "--sp-biz-type",
        type=int,
        default=None,
        help="Industry type filter when listing categories",
    )
    probe.set_defaults(func=cmd_probe)

    list_wins = sub.add_parser("list-wins", help="List real wins not yet listed")
    list_wins.add_argument(
        "--include-listed",
        action="store_true",
        help="Include already listed ids",
    )
    list_wins.set_defaults(func=cmd_list_wins)

    draft = sub.add_parser("draft", help="Build rewritten title/content draft for a win id")
    draft.add_argument("--id", required=True, help="CardHobby item id")
    draft.set_defaults(func=cmd_draft)

    prepare = sub.add_parser(
        "prepare-image",
        help="Crop CardHobby image to card face; optionally upload to OSS",
    )
    prepare.add_argument("--id", required=True, help="CardHobby item id")
    prepare.add_argument(
        "--force",
        action="store_true",
        help="Re-crop even if state/crops/{id}.jpg exists",
    )
    prepare.add_argument(
        "--upload",
        action="store_true",
        help="Upload cropped JPEG to IMAGE_OSS_* and print public URL",
    )
    prepare.set_defaults(func=cmd_prepare_image)

    create = sub.add_parser(
        "create-unpublished",
        help="Crop+upload then create product (never uses watermarked source URL)",
    )
    create.add_argument("--id", required=True, help="CardHobby item id")
    create.add_argument("--title", default=None, help="Override generated title")
    create.add_argument(
        "--price-yuan",
        type=float,
        default=None,
        help="Override suggested price in yuan",
    )
    create.add_argument(
        "--title-prefix",
        default="[测试]",
        help="Prefix for safety; pass empty string to disable",
    )
    create.add_argument(
        "--force",
        action="store_true",
        help="Create even if state says already listed",
    )
    create.add_argument(
        "--force-crop",
        action="store_true",
        help="Re-run card crop before upload",
    )
    create.set_defaults(func=cmd_create_unpublished)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()
    try:
        code = args.func(args, settings)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ValueError, ImagePrepareError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
