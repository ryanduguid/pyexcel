"""Generated suffixes must preserve sheets that already use those names."""
import operator

import pytest

from pyexcel import Book, Sheet
from pyexcel import book


@pytest.mark.parametrize("combine", [operator.add, operator.iadd])
def test_generated_name_skips_every_existing_sheet(monkeypatch, combine):
    monkeypatch.setattr(book, "LOCAL_UUID", 0)
    original = {"A": [[1]], "A_1": [[2]], "A_2": [[3]]}
    existing = Book(original)
    incoming = Sheet([[4]], "A")
    result = combine(existing, incoming)
    assert result.to_dict() == {**original, "A_3": [[4]]}
    assert incoming.array == [[4]]
