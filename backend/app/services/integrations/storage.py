"""Object storage abstraction: local filesystem for dev, S3 for production."""

import asyncio
import shutil
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class ObjectStorage(Protocol):
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str: ...
    async def put_file(self, key: str, path: Path, content_type: str) -> str: ...
    async def download_to(self, key: str, path: Path) -> Path: ...
    async def url_for(self, key: str) -> str: ...


class LocalObjectStorage:
    def __init__(self, root: str, public_base_url: str = "file://") -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._public_base_url = public_base_url

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root.resolve() not in path.parents:
            raise ValueError("Invalid storage key")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(self._path(key).write_bytes, data)
        return key

    async def put_file(self, key: str, path: Path, content_type: str) -> str:
        await asyncio.to_thread(shutil.copyfile, path, self._path(key))
        return key

    async def download_to(self, key: str, path: Path) -> Path:
        await asyncio.to_thread(shutil.copyfile, self._path(key), path)
        return path

    async def url_for(self, key: str) -> str:
        return f"{self._public_base_url}{self._path(key)}"


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        import boto3

        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required for the s3 storage backend")
        self._bucket = settings.s3_bucket
        self._expiry = settings.s3_presign_expiry_seconds
        self._client = boto3.client(
            "s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint_url
        )

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )
        return key

    async def put_file(self, key: str, path: Path, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.upload_file, str(path), self._bucket, key, ExtraArgs={"ContentType": content_type}
        )
        return key

    async def download_to(self, key: str, path: Path) -> Path:
        await asyncio.to_thread(self._client.download_file, self._bucket, key, str(path))
        return path

    async def url_for(self, key: str) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=self._expiry,
        )


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "s3":
        return S3ObjectStorage(settings)
    return LocalObjectStorage(settings.local_storage_path)
