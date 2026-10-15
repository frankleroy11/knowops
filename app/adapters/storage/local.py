# 中文导读：
# 本地文件存储边界：限制上传大小、生成独立文件名并计算摘要
# 删除时必须约束路径，不能把客户端文件名直接当成磁盘路径

"""本地磁盘存储：上传文件的落盘、限额与指纹。

此前这段逻辑内联在 `knowledge/router.py`（HTTP 层）里。迁移到适配器后：

- 后缀/大小/空文件校验在存储层完成，错误以 `StorageError` 子类抛出，
  由路由映射为 415/413/422，存储层不依赖 FastAPI；
- 落盘名用随机 UUID，不用原始文件名直接作为路径；
- 任何失败（含超限）都会删除半成品文件，不留垃圾。
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

ALLOWED_SUFFIXES = frozenset({".txt", ".md", ".pdf"})
READ_CHUNK = 64 * 1024


class StorageError(Exception):
    """存储层错误基类；路由层据此决定 HTTP 状态码。"""


class UnsupportedFormat(StorageError):
    pass


class FileTooLarge(StorageError):
    pass


class EmptyFile(StorageError):
    pass


@dataclass(frozen=True)
class StoredFile:
    filename: str
    storage_name: str
    content_hash: str
    size: int


class LocalStorage:
    def __init__(self, root: Path, max_bytes: int = 10 * 1024 * 1024):
        self.root = Path(root)
        self.max_bytes = max_bytes

    @property
    def directory(self) -> Path:
        return self.root / "storage"

    def path(self, storage_name: str) -> Path:
        return self.directory / storage_name

    def save(self, file, original_name: str | None = None) -> StoredFile:
        """Persist an upload stream and return its identity."""
        raw_name = original_name or getattr(file, "filename", "") or ""
        name = raw_name.replace("\\", "/").split("/")[-1]
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise UnsupportedFormat("仅支持 TXT、Markdown、文本 PDF")
        if len(name) > 255:
            raise StorageError("文件名过长")
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / (uuid4().hex + suffix)
        digest = hashlib.sha256()
        total = 0
        committed = False
        try:
            with target.open("xb") as output:
                while data := file.file.read(READ_CHUNK):
                    total += len(data)
                    if total > self.max_bytes:
                        raise FileTooLarge("文件不能超过 10 MiB")
                    digest.update(data)
                    output.write(data)
            if total == 0:
                raise EmptyFile("文件为空")
            committed = True
        finally:
            file.file.close()
            if not committed:
                target.unlink(missing_ok=True)
        return StoredFile(
            filename=name,
            storage_name=target.name,
            content_hash=digest.hexdigest(),
            size=total,
        )

    def checked_delete_path(self, storage_name: str) -> Path:
        if (
            not storage_name
            or Path(storage_name).name != storage_name
            or storage_name in {".", ".."}
        ):
            raise StorageError("存储文件名不合法")
        return self.path(storage_name)

    def delete(self, storage_name: str) -> bool:
        target = self.checked_delete_path(storage_name)
        if target.is_file():
            target.unlink()
            return True
        return False
