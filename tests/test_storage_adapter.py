"""Storage adapter: limits, naming and cleanup behaviour."""

import io

import pytest

from app.adapters.storage import (
    EmptyFile,
    FileTooLarge,
    LocalStorage,
    StorageError,
    UnsupportedFormat,
)


class FakeUpload:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self.file = io.BytesIO(data)


def test_save_returns_identity_and_writes_the_file(tmp_path):
    storage = LocalStorage(tmp_path)
    stored = storage.save(FakeUpload("vpn.md", b"hello world"))
    assert stored.filename == "vpn.md"
    assert stored.size == 11
    stem, _, suffix = stored.storage_name.partition(".")
    assert suffix == "md" and len(stem) == 32 and int(stem, 16) >= 0
    assert stored.content_hash == __import__("hashlib").sha256(b"hello world").hexdigest()
    assert storage.path(stored.storage_name).read_bytes() == b"hello world"


def test_client_supplied_paths_are_stripped(tmp_path):
    stored = LocalStorage(tmp_path).save(FakeUpload("../../etc/passwd.md", b"x"))
    assert stored.filename == "passwd.md"
    assert "/" not in stored.storage_name


@pytest.mark.parametrize("name", ["notes.exe", "archive.zip", "noext"])
def test_unsupported_suffixes_are_rejected(tmp_path, name):
    with pytest.raises(UnsupportedFormat):
        LocalStorage(tmp_path).save(FakeUpload(name, b"x"))


def test_empty_upload_is_rejected_and_leaves_nothing(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(EmptyFile):
        storage.save(FakeUpload("empty.md", b""))
    assert list(storage.directory.iterdir()) == []


def test_oversized_upload_is_rejected_and_leaves_nothing(tmp_path):
    storage = LocalStorage(tmp_path, max_bytes=1024)
    with pytest.raises(FileTooLarge):
        storage.save(FakeUpload("big.md", b"a" * 2048))
    assert list(storage.directory.iterdir()) == []


def test_long_names_are_rejected(tmp_path):
    with pytest.raises(StorageError):
        LocalStorage(tmp_path).save(FakeUpload("a" * 300 + ".md", b"x"))


def test_delete_removes_only_known_files(tmp_path):
    storage = LocalStorage(tmp_path)
    stored = storage.save(FakeUpload("a.md", b"x"))
    assert storage.delete(stored.storage_name) is True
    assert storage.delete(stored.storage_name) is False
