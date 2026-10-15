# 中文导读：
# 识别未被数据库引用的本地文件，默认预览；只有显式清理才删除，不能把仍有引用的文件作为孤儿处理

"""Find (and optionally remove) uploaded files no longer referenced by any version.

DB 行删除时不会自动清理 `storage/` 下的文件，所以历史上会积累孤儿文件。
本脚本以 `document_versions.storage_path` 为准，列出未被引用的文件；`--delete` 才会真正删除。

用法：
    python scripts/storage_gc.py            # 只列出（默认）
    python scripts/storage_gc.py --delete   # 删除孤儿文件
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.adapters.storage import LocalStorage
from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.knowledge.models import DocumentVersion


def find_orphans(referenced: set[str], present: set[str]) -> list[str]:
    """Files on disk that no version row points at; dotfiles are ignored."""
    candidates = {name for name in present if not name.startswith(".")}
    return sorted(candidates - referenced)


def main() -> None:
    parser = argparse.ArgumentParser(description="清理未被任何文档版本引用的上传文件")
    parser.add_argument("--delete", action="store_true", help="真正删除（默认只列出）")
    args = parser.parse_args()

    storage = LocalStorage(ROOT)
    if not storage.directory.is_dir():
        print("storage 目录不存在，无需处理")
        return
    with SessionLocal() as db:
        referenced = set(db.scalars(select(DocumentVersion.storage_path)))
    present = {path.name for path in storage.directory.iterdir() if path.is_file()}
    orphans = find_orphans(referenced, present)

    print(f"引用中的文件 {len(referenced)} 个，目录内 {len(present)} 个，孤儿 {len(orphans)} 个")
    for name in orphans:
        print(f"  {name}")
    if not args.delete:
        if orphans:
            print("（默认只列出；确认后加 --delete 删除）")
        return
    removed = sum(1 for name in orphans if storage.delete(name))
    print(f"已删除 {removed} 个孤儿文件")


if __name__ == "__main__":
    main()
