"""
阿里云 OSS 上传工具。

使用方式：
    from app.utils.oss import oss_client

    # 上传文件路径
    url = oss_client.upload_file("/tmp/shot_001.png", directory="shots/scene_001")

    # 上传二进制内容（如内存中的图片）
    url = oss_client.upload_bytes(image_bytes, filename="cover.jpg", directory="covers")

    # 删除文件
    oss_client.delete("shots/scene_001/shot_001.png")

    # 生成临时访问链接（私有 bucket 使用）
    signed_url = oss_client.sign_url("shots/scene_001/shot_001.png", expires=3600)
"""

import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import oss2

from app.core.config import settings


class OSSClient:
    """阿里云 OSS 客户端封装。

    所有上传路径格式：{OSS_BASE_DIR}/{directory}/{filename}
    例如：filmgenx/shots/scene_001/abc123_shot_001.png
    """

    def __init__(self) -> None:
        self._bucket: Optional[oss2.Bucket] = None

    def _get_bucket(self) -> oss2.Bucket:
        """懒加载 Bucket 实例，首次调用时初始化。"""
        if self._bucket is None:
            if not all([
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET,
                settings.OSS_BUCKET_NAME,
                settings.OSS_ENDPOINT,
            ]):
                raise RuntimeError(
                    "OSS 配置不完整，请检查 .env 中的 OSS_ACCESS_KEY_ID / "
                    "OSS_ACCESS_KEY_SECRET / OSS_BUCKET_NAME / OSS_ENDPOINT"
                )
            auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
            self._bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
        return self._bucket

    def _build_object_key(self, filename: str, directory: Optional[str] = None) -> str:
        """构建 OSS 对象完整路径。

        路径结构：{OSS_BASE_DIR}/{env_prefix}/{directory}/{filename}
          - dev  环境：filmgenx/dev/shots/scene_001/shot.png
          - prod 环境：filmgenx/prod/shots/scene_001/shot.png

        Args:
            filename:  文件名，如 shot_001.png
            directory: 相对目录，如 shots/scene_001。为空时直接放在环境目录下。

        Returns:
            完整对象路径，如 filmgenx/dev/shots/scene_001/shot_001.png
        """
        env_prefix = "prod" if settings.APP_ENV == "production" else "dev"
        parts = [settings.OSS_BASE_DIR.strip("/"), env_prefix]
        if directory:
            parts.append(directory.strip("/"))
        parts.append(filename)
        return "/".join(parts)

    def _build_url(self, object_key: str) -> str:
        """将对象路径转换为访问 URL。

        优先使用 CDN 域名（OSS_CDN_DOMAIN），否则使用 OSS 默认域名。
        """
        if settings.OSS_CDN_DOMAIN:
            base = settings.OSS_CDN_DOMAIN.rstrip("/")
            return f"{base}/{object_key}"
        endpoint = settings.OSS_ENDPOINT.rstrip("/")
        bucket = settings.OSS_BUCKET_NAME
        # OSS 默认 URL 格式：https://{bucket}.{endpoint}/{key}
        if endpoint.startswith("http"):
            protocol, host = endpoint.split("://", 1)
            return f"{protocol}://{bucket}.{host}/{object_key}"
        return f"https://{bucket}.{endpoint}/{object_key}"

    def upload_file(
        self,
        local_path: str | Path,
        *,
        directory: Optional[str] = None,
        filename: Optional[str] = None,
        unique: bool = True,
    ) -> str:
        """上传本地文件到 OSS。

        Args:
            local_path: 本地文件路径。
            directory:  OSS 目标目录，如 "shots/scene_001"。
            filename:   覆盖原始文件名。为空时使用本地文件名。
            unique:     True 时在文件名前加 UUID 前缀，防止同名覆盖。

        Returns:
            文件的完整访问 URL。
        """
        local_path = Path(local_path)
        name = filename or local_path.name
        if unique:
            stem = local_path.stem if not filename else Path(filename).stem
            suffix = local_path.suffix if not filename else Path(filename).suffix
            name = f"{uuid.uuid4().hex[:8]}_{stem}{suffix}"

        object_key = self._build_object_key(name, directory)
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        self._get_bucket().put_object_from_file(
            object_key,
            str(local_path),
            headers={"Content-Type": content_type},
        )
        return self._build_url(object_key)

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        directory: Optional[str] = None,
        unique: bool = True,
    ) -> str:
        """上传内存中的二进制数据到 OSS。

        Args:
            data:      文件二进制内容。
            filename:  文件名，用于推断 Content-Type，如 "cover.jpg"。
            directory: OSS 目标目录，如 "covers"。
            unique:    True 时在文件名前加 UUID 前缀，防止同名覆盖。

        Returns:
            文件的完整访问 URL。
        """
        name = filename
        if unique:
            p = Path(filename)
            name = f"{uuid.uuid4().hex[:8]}_{p.stem}{p.suffix}"

        object_key = self._build_object_key(name, directory)
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        self._get_bucket().put_object(
            object_key,
            data,
            headers={"Content-Type": content_type},
        )
        return self._build_url(object_key)

    def delete(self, object_key: str) -> None:
        """删除 OSS 上的文件。

        Args:
            object_key: 完整对象路径，如 filmgenx/shots/scene_001/shot_001.png。
                        可直接传 upload_file / upload_bytes 返回的 URL 对应的路径部分。
        """
        self._get_bucket().delete_object(object_key)

    def delete_by_url(self, url: str) -> None:
        """通过访问 URL 删除 OSS 上的文件。

        Args:
            url: upload_file / upload_bytes 返回的完整 URL。
        """
        if settings.OSS_CDN_DOMAIN:
            base = settings.OSS_CDN_DOMAIN.rstrip("/") + "/"
            object_key = url.replace(base, "", 1)
        else:
            # 从 URL 中截取 object key（去掉协议和域名部分）
            parts = url.split("/", 3)
            object_key = parts[3] if len(parts) > 3 else url
        self.delete(object_key)

    def sign_url(self, object_key: str, expires: int = 3600) -> str:
        """生成带签名的临时访问链接（适用于私有 Bucket）。

        Args:
            object_key: 完整对象路径。
            expires:    链接有效期（秒），默认 1 小时。

        Returns:
            带签名的临时访问 URL。
        """
        return self._get_bucket().sign_url("GET", object_key, expires)

    def exists(self, object_key: str) -> bool:
        """检查 OSS 上的文件是否存在。"""
        return oss2.ObjectIterator(self._get_bucket(), prefix=object_key, max_keys=1).__iter__().__next__() is not None if False else self._get_bucket().object_exists(object_key)

    def download_and_upload(
        self,
        url: str,
        *,
        directory: Optional[str] = None,
        filename: Optional[str] = None,
        unique: bool = True,
        timeout: float = 60.0,
    ) -> str:
        """下载临时 URL 文件并上传到 OSS。

        用于处理 AI 生成服务（如 Kling、Evolink）返回的临时 URL，
        将文件持久化存储到自己的 CDN。

        Args:
            url:       临时文件 URL。
            directory: OSS 目标目录，如 "videos/shots"。
            filename:  自定义文件名。为空时从 URL 路径推断。
            unique:    True 时在文件名前加 UUID 前缀，防止同名覆盖。
            timeout:   下载超时时间（秒），默认 60 秒。

        Returns:
            OSS 上的永久访问 URL。

        Raises:
            httpx.HTTPError: 下载失败时抛出。
        """
        # 从 URL 推断文件名
        if not filename:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            filename = path.split("/")[-1] if "/" in path else "downloaded_file"

        # 下载文件
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.content

        # 上传到 OSS
        return self.upload_bytes(
            data,
            filename=filename,
            directory=directory,
            unique=unique,
        )


# 全局单例，直接 import 使用
oss_client = OSSClient()
