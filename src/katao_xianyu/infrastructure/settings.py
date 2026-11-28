from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from katao_xianyu.application.build_draft import PricingConfig
from katao_xianyu.application.publish_listing import ChannelPropertyValue, ShopPublishConfig
from katao_xianyu.infrastructure.oss_image_host import OssImageHostConfig

# 球星卡类目「成色=品相完好无瑕疵」（probe pv/list 实测）
_DEFAULT_CONDITION_PV = ChannelPropertyValue(
    property_id="3b9f06b2bccead76",
    property_name="成色",
    value_id="38fb2f464f74f87b14cfee7282107eb6",
    value_name="品相完好无瑕疵",
)


def _project_root() -> Path:
    # src/katao_xianyu/infrastructure/settings.py → repo root
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    goofish_app_key: str
    goofish_app_secret: str
    goofish_debug: bool
    shop: ShopPublishConfig
    pricing: PricingConfig
    results_dir: Path
    runs_dir: Path
    listing_state_path: Path
    crops_dir: Path
    image_oss: OssImageHostConfig
    image_oss_key_prefix: str

    @property
    def goofish_ready(self) -> bool:
        return bool(self.goofish_app_key and self.goofish_app_secret)

    @property
    def image_host_ready(self) -> bool:
        return self.image_oss.ready


def _int_env(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return float(raw)


def load_settings(env_file: Path | None = None) -> Settings:
    root = _project_root()
    dotenv_path = env_file or (root / ".env")
    if dotenv_path.is_file():
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    results = Path(
        os.getenv(
            "XIANYUJIANLOU_RESULTS_DIR",
            r"D:\xianyujianlou-settlement-serial\results",
        )
    )
    runs = Path(os.getenv("XIANYUJIANLOU_RUNS_DIR", r"D:\xianyujianlou\runs"))
    state_raw = os.getenv("LISTING_STATE_PATH", "state/listing-state.json")
    state_path = Path(state_raw)
    if not state_path.is_absolute():
        state_path = root / state_path

    crops_raw = os.getenv("CROPS_DIR", "state/crops")
    crops_dir = Path(crops_raw)
    if not crops_dir.is_absolute():
        crops_dir = root / crops_dir

    image_oss = OssImageHostConfig(
        endpoint=os.getenv("IMAGE_OSS_ENDPOINT", "").strip(),
        bucket=os.getenv("IMAGE_OSS_BUCKET", "").strip(),
        access_key=os.getenv("IMAGE_OSS_ACCESS_KEY", "").strip(),
        secret_key=os.getenv("IMAGE_OSS_SECRET_KEY", "").strip(),
        public_base_url=os.getenv("IMAGE_OSS_PUBLIC_BASE_URL", "").strip(),
        region=os.getenv("IMAGE_OSS_REGION", "").strip(),
        addressing_style=os.getenv("IMAGE_OSS_ADDRESSING_STYLE", "virtual").strip()
        or "virtual",
    )
    image_oss_key_prefix = (
        os.getenv("IMAGE_OSS_KEY_PREFIX", "katao-xianyu/crops/").strip()
        or "katao-xianyu/crops/"
    )

    condition_name = os.getenv("GOOFISH_CONDITION_VALUE_NAME", "品相完好无瑕疵").strip()
    channel_pv: tuple[ChannelPropertyValue, ...] = ()
    if condition_name:
        # Allow override of IDs; default matches 球星卡「完好」
        channel_pv = (
            ChannelPropertyValue(
                property_id=os.getenv(
                    "GOOFISH_CONDITION_PROPERTY_ID", _DEFAULT_CONDITION_PV.property_id
                ).strip()
                or _DEFAULT_CONDITION_PV.property_id,
                property_name=os.getenv("GOOFISH_CONDITION_PROPERTY_NAME", "成色").strip()
                or "成色",
                value_id=os.getenv(
                    "GOOFISH_CONDITION_VALUE_ID", _DEFAULT_CONDITION_PV.value_id
                ).strip()
                or _DEFAULT_CONDITION_PV.value_id,
                value_name=condition_name,
            ),
        )

    shop = ShopPublishConfig(
        user_name=os.getenv("GOOFISH_SHOP_USER", "").strip(),
        province=_int_env("GOOFISH_PROVINCE"),
        city=_int_env("GOOFISH_CITY"),
        district=_int_env("GOOFISH_DISTRICT"),
        express_fee_fen=_int_env("GOOFISH_EXPRESS_FEE_FEN"),
        sp_biz_type=_int_env("GOOFISH_SP_BIZ_TYPE"),
        channel_cat_id=os.getenv("GOOFISH_CHANNEL_CAT_ID", "").strip(),
        channel_pv=channel_pv,
    )
    pricing = PricingConfig(
        markup_ratio=_float_env("PRICE_MARKUP_RATIO", 1.35),
        markup_fen=_int_env("PRICE_MARKUP_FEN"),
        stuff_status=_int_env("GOOFISH_STUFF_STATUS"),
    )
    debug_raw = os.getenv("GOOFISH_DEBUG", "1").strip().lower()
    debug = debug_raw in {"1", "true", "yes", "on"}

    return Settings(
        goofish_app_key=os.getenv("GOOFISH_APP_KEY", "").strip(),
        goofish_app_secret=os.getenv("GOOFISH_APP_SECRET", "").strip(),
        goofish_debug=debug,
        shop=shop,
        pricing=pricing,
        results_dir=results,
        runs_dir=runs,
        listing_state_path=state_path,
        crops_dir=crops_dir,
        image_oss=image_oss,
        image_oss_key_prefix=image_oss_key_prefix,
    )
