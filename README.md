# katao-xianyu

把 **xianyujianlou LIVE 中标** 通过闲管家官方 API 上架到闲鱼。

竞拍仓已有标题素材、卡淘 CDN 图片、`identity` 结构化字段。本项目**不建 PostgreSQL**，只做：组装草稿（**重写标题/描述**）→ 人工确认 → API 创建商品。

## 分层架构

依赖只向内：`interfaces → application → domain`，`infrastructure` 实现 application 端口。

```text
src/katao_xianyu/
  domain/           # 实体、标题/定价纯函数（无 I/O）
  application/      # 用例 + ports（Protocol）
  infrastructure/   # LIVE JSON、listing-state.json、Goofish SDK、.env
  interfaces/       # CLI 组合根（日后可加 HTTP）
```

| 层 | 职责 |
| --- | --- |
| domain | `WonCard` / `ListingDraft`；`build_title` / `build_content` / `suggest_price_fen` |
| application | `ListPendingWins` / `BuildDraft` / `PrepareListingImage` / `PublishListing` / `ProbeShop` |
| infrastructure | `LiveJsonWinSource` / `OpenCvCardCropper` / `S3CompatibleImageHost` / `GoofishGateway` / `Settings` |
| interfaces | `cli.py`：装依赖、调用例 |

禁止：`domain` 读文件或调 HTTP；`interfaces` 直接拼业务规则或直接 import `goofish_api`。

## 快速开始

```powershell
cd D:\katao-xianyu
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# 编辑 .env：填入 GOOFISH_APP_KEY / GOOFISH_APP_SECRET / 店铺与类目等
```

```powershell
python -m katao_xianyu probe
python -m katao_xianyu probe --categories --sp-biz-type 28
python -m katao_xianyu list-wins
python -m katao_xianyu draft --id 153282293
# 卡面裁切（去掉周边卖家水印）；先看本地 crops
python -m katao_xianyu prepare-image --id 145561105 --force
# 配置 IMAGE_OSS_* 后上传，再创建
python -m katao_xianyu prepare-image --id 145561105 --upload
python -m katao_xianyu create-unpublished --id 145561105
```

## 商品图（卡面裁切）

卡淘原图常有「拔脚」等周边水印，**禁止直接当闲鱼主图**。

1. OpenCV 自动检出卡面矩形并裁切 → `state/crops/{id}.jpg`  
2. 上传到 S3 兼容对象存储（`IMAGE_OSS_*`）得到公网 URL  
3. `create-unpublished` **只**用裁切后的公网 URL；未配置 OSS 或裁切失败则报错，不回退原图  

局限：水印若盖在**卡面正中**，裁切去不掉，需以后实拍或 AI。

## 配置

见 [.env.example](.env.example)。密钥只放本地 `.env`，不要提交。

- `XIANYUJIANLOU_RESULTS_DIR`：含 `*-LIVE/live-summary.json`
- `XIANYUJIANLOU_RUNS_DIR`：含 `*/list.json`（补 image / identity）
- `GOOFISH_CHANNEL_CAT_ID` / `GOOFISH_SP_BIZ_TYPE`：Phase 0 `probe --categories` 后写入
- `IMAGE_OSS_*`：裁切图公网托管（发布前必填）

## 测试

```powershell
pytest
```

## 阶段

1. Phase 0：`probe` + 类目冻结 + 卡面裁切 + `create-unpublished`  
2. Phase 1：确认后正式上架 + state 防重  
3. 后续：订单同步、标题增强
