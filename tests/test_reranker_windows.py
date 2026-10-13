import pytest

from scripts.audit_reranker import token_windows


class CharacterTokenizer:
    def __call__(self, text, pair=None, **kwargs):
        result = {"input_ids": list(range(len(text) + (len(pair) + 2 if pair is not None else 0)))}
        if kwargs.get("return_offsets_mapping"):
            result["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return result

    def num_special_tokens_to_add(self, pair):
        return 2


def test_windows_cover_document_tail_with_overlap():
    windows = token_windows(CharacterTokenizer(), "问题", "abcdefghijkl", max_length=10, overlap=2)
    assert windows == ["abcdef", "efghij", "ijkl"]
    assert all(len(w) <= 6 for w in windows)
    assert windows[-1].endswith("kl")


def test_short_and_empty_documents():
    assert token_windows(CharacterTokenizer(), "问题", "abc", max_length=10, overlap=2) == ["abc"]
    assert token_windows(CharacterTokenizer(), "问题", "", max_length=10, overlap=2) == [""]


def test_query_must_leave_room_for_overlap():
    with pytest.raises(ValueError):
        token_windows(CharacterTokenizer(), "很长的问题", "abc", max_length=8, overlap=2)


def test_retokenized_boundary_cannot_exceed_budget():
    class BoundaryTokenizer(CharacterTokenizer):
        def __call__(self, text, pair=None, **kwargs):
            result = super().__call__(text, pair, **kwargs)
            if pair is not None:
                result["input_ids"].append(999)
            return result

    tokenizer = BoundaryTokenizer()
    windows = token_windows(tokenizer, "问题", "abcdefghijkl", max_length=10, overlap=2)
    assert windows == ["abcde", "defgh", "ghijk", "jkl"]
    assert all(len(tokenizer("问题", w)["input_ids"]) <= 10 for w in windows)
