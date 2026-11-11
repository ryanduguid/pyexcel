from textwrap import dedent

import pytest
from pyexcel import Sheet

from .nose_tools import eq_


@pytest.mark.parametrize("named", [False, True])
def test_grouping_by_column_name_includes_one_header_per_group(named):
    sheet = Sheet(
        [["category", "value"], ["a", 1], ["b", 2], ["a", 3]],
        name_columns_by_row=0 if named else -1,
    )
    book = sheet.group_rows_by_column("category")
    assert book.to_dict() == {
        "a": [["category", "value"], ["a", 1], ["a", 3]],
        "b": [["category", "value"], ["b", 2]],
    }
    assert sheet.colnames == ["category", "value"]


def test_unnamed_sheet_cannot_be_converted_to_a_named_dictionary():
    with pytest.raises(NotImplementedError, match="Not implemented"):
        Sheet([[1, 2]]).to_dict()


def test_named_rows_include_an_empty_row_for_an_extra_name():
    sheet = Sheet([[1]], rownames=["data", "empty"])
    assert list(sheet.named_rows()) == [{"data": [1]}, {"empty": []}]


def test_named_tuple_access_resolves_both_axes():
    sheet = Sheet([[1, 2], [3, 4]], rownames=["r1", "r2"], colnames=["a", "b"])
    assert sheet["r2", "a"] == 3
    assert sheet[0, "b"] == 2


def test_project():
    sheet = Sheet(
        [["A", "B", "C"], [1, 2, 3], [11, 22, 33], [111, 222, 333]],
        name_columns_by_row=0,
    )
    expected = dedent(
        """
    pyexcel sheet:
    +-----+-----+-----+
    |  B  |  A  |  C  |
    +=====+=====+=====+
    | 2   | 1   | 3   |
    +-----+-----+-----+
    | 22  | 11  | 33  |
    +-----+-----+-----+
    | 222 | 111 | 333 |
    +-----+-----+-----+""",
    ).strip()
    sheet = sheet.project(["B", "A", "C"])
    eq_(expected, str(sheet))


def test_project_for_less():
    sheet = Sheet(
        [["A", "B", "C"], [1, 2, 3], [11, 22, 33], [111, 222, 333]],
        name_columns_by_row=0,
    )
    expected = dedent(
        """
    pyexcel sheet:
    +-----+-----+
    |  B  |  C  |
    +=====+=====+
    | 2   | 3   |
    +-----+-----+
    | 22  | 33  |
    +-----+-----+
    | 222 | 333 |
    +-----+-----+""",
    ).strip()
    sheet = sheet.project(["B", "C"])
    eq_(expected, str(sheet))


def test_project_for_exclusion():
    sheet = Sheet(
        [["A", "B", "C"], [1, 2, 3], [11, 22, 33], [111, 222, 333]],
        name_columns_by_row=0,
    )
    expected = dedent(
        """
    pyexcel sheet:
    +-----+
    |  A  |
    +=====+
    | 1   |
    +-----+
    | 11  |
    +-----+
    | 111 |
    +-----+""",
    ).strip()
    sheet = sheet.project(["B", "C"], exclusion=True)
    eq_(expected, str(sheet))
