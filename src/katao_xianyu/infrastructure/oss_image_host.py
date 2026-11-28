from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin


@dataclass(frozen=True)
class OssImageHostConfig:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    public_base_url: str
    region: str = ""
    addressing_style: str = "virtual"  # virtual | path

    @property
    def ready(self) -> bool:
        return bool(
            self.endpoint
            and self.bucket
            and self.access_key
            and self.secret_key
            and self.public_base_url
        )


class UnconfiguredImageHost:
    def is_configured(self) -> bool:
        return False

    def upload(self, *, object_key: str, file_path: Path, content_type: str = "image/jpeg") -> str:
        raise RuntimeError(
            "IMAGE_OSS_* is not configured; cannot upload cropped images"
        )


class S3CompatibleImageHost:
    """Upload via boto3 to S3-compatible storage (Aliyun OSS S3 API, R2, MinIO, …)."""

    def __init__(self, config: OssImageHostConfig) -> None:
        if not config.ready:
            raise ValueError("incomplete OSS config")
        self._config = config
        import boto3
        from botocore.config import Config as BotoConfig

        addressing = (
            "path" if config.addressing_style == "path" else "virtual"
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint.rstrip("/"),
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region or None,
            config=BotoConfig(s3={"addressing_style": addressing}),
        )

    def is_configured(self) -> bool:
        return True

    def upload(self, *, object_key: str, file_path: Path, content_type: str = "image/jpeg") -> str:
        key = object_key.lstrip("/")
        with file_path.open("rb") as fh:
            self._client.put_object(
                Bucket=self._config.bucket,
                Key=key,
                Body=fh,
                ContentType=content_type,
            )
        base = self._config.public_base_url.rstrip("/") + "/"
        return urljoin(base, key)


def build_image_host(config: OssImageHostConfig | None) -> UnconfiguredImageHost | S3CompatibleImageHost:
    if config is None or not config.ready:
        return UnconfiguredImageHost()
    return S3CompatibleImageHost(config)
