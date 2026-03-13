from __future__ import annotations

import os
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
    def save(self, *, original_name: str, content: bytes) -> StoredFileInfo:
        # Extension point for production object storage integration.
        raise NotImplementedError("S3-compatible storage provider is not configured in this MVP")

    def delete(self, *, key: str, path: str | None = None) -> None:
        raise NotImplementedError("S3-compatible storage provider is not configured in this MVP")


def build_storage_provider() -> FileStorageProvider:
    provider = settings.FILE_STORAGE_PROVIDER.lower().strip()
    if provider == "s3":
        return S3CompatibleFileStorageProvider()
    return LocalFileStorageProvider(settings.UPLOAD_DIR)
