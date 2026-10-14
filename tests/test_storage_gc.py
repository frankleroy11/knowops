"""Storage garbage collection: orphan detection."""

from scripts.storage_gc import find_orphans


def test_only_unreferenced_files_are_reported():
    assert find_orphans({"a.md", "b.md"}, {"a.md", "b.md", "c.md"}) == ["c.md"]


def test_dotfiles_are_ignored():
    assert find_orphans(set(), {".gitkeep", "real.md"}) == ["real.md"]


def test_output_is_sorted_and_referenced_files_are_kept():
    assert find_orphans({"keep.md"}, {"z.md", "keep.md", "a.md"}) == ["a.md", "z.md"]
