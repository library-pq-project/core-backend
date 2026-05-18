from __future__ import annotations

import os
import mimetypes
import uuid
from dataclasses import dataclass
from typing import Protocol

from src.core.config import settings


@dataclass
class StoredFileInfo:
    provider: str
    bucket: str | None
    key: str
    path: str


class FileStorageProvider(Protocol):
    def save(self, *, original_name: str, content: bytes) -> StoredFileInfo:
        ...

    def delete(self, *, key: str, path: str | None = None) -> None:
        ...


class LocalFileStorageProvider:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save(self, *, original_name: str, content: bytes) -> StoredFileInfo:
        extension = original_name.split(".")[-1].lower() if "." in original_name else "bin"
        unique_name = f"{uuid.uuid4().hex}.{extension}"
        full_path = os.path.join(self.base_dir, unique_name)
        with open(full_path, "wb") as output_file:
            output_file.write(content)
        return StoredFileInfo(provider="local", bucket=None, key=unique_name, path=full_path)

    def delete(self, *, key: str, path: str | None = None) -> None:
        target = path or os.path.join(self.base_dir, key)
        if os.path.exists(target):
            os.remove(target)


class S3CompatibleFileStorageProvider:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        endpoint_from_env = (settings.S3_ENDPOINT_URL or "").strip()
        if not endpoint_from_env and settings.R2_ACCOUNT_ID:
            endpoint_from_env = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        if endpoint_from_env and "://" not in endpoint_from_env:
            endpoint_from_env = f"https://{endpoint_from_env}"
        self.endpoint_url = endpoint_from_env or None
        self.is_r2 = bool(self.endpoint_url and "r2.cloudflarestorage.com" in self.endpoint_url)
        self.region = "auto" if self.is_r2 else settings.S3_REGION
        self.prefix = settings.S3_KEY_PREFIX.strip("/")
        self.addressing_style = settings.S3_ADDRESSING_STYLE.strip().lower() or "auto"
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        if not self.bucket:
            raise RuntimeError("S3_BUCKET_NAME is required when FILE_STORAGE_PROVIDER=s3")
        if not self.access_key or not self.secret_key:
            raise RuntimeError("S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY are required for S3 storage")
        self._client = self._build_client()

    def _build_client(self):
        try:
            import boto3
            from botocore.config import Config
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("boto3 is required for FILE_STORAGE_PROVIDER=s3. Install dependencies.") from exc
        effective_addressing_style = self.addressing_style
        if self.is_r2 and effective_addressing_style == "auto":
            effective_addressing_style = "path"
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": effective_addressing_style},
            ),
        )

    def _build_key(self, original_name: str) -> str:
        extension = original_name.split(".")[-1].lower() if "." in original_name else "bin"
        filename = f"{uuid.uuid4().hex}.{extension}"
        if self.prefix:
            return f"{self.prefix}/{filename}"
        return filename

    def save(self, *, original_name: str, content: bytes) -> StoredFileInfo:
        key = self._build_key(original_name)
        content_type, _ = mimetypes.guess_type(original_name)
        put_kwargs = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": content,
        }
        if content_type:
            put_kwargs["ContentType"] = content_type
        self._client.put_object(**put_kwargs)
        return StoredFileInfo(
            provider="s3",
            bucket=self.bucket,
            key=key,
            path=f"s3://{self.bucket}/{key}",
        )

    def delete(self, *, key: str, path: str | None = None) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)


def build_storage_provider() -> FileStorageProvider:
    provider = settings.FILE_STORAGE_PROVIDER.lower().strip()
    if provider == "s3":
        return S3CompatibleFileStorageProvider()
    return LocalFileStorageProvider(settings.UPLOAD_DIR)
