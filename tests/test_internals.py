import io
from unittest.mock import MagicMock

import pytest
from pyexcel._compact import append_doc
from pyexcel.internal.core import _seek_at_zero
from pyexcel.internal.utils import make_a_property
from pyexcel.internal.sheets.matrix import Matrix, uniform
from pyexcel.internal.sheets._shared import CommonPropertyAmongRowNColumn


def test_seek_at_zero():
    stream = MagicMock()
    stream.seek.side_effect = io.UnsupportedOperation()
    _seek_at_zero(stream)


def test_append_doc_preserves_an_undocumented_function():
    def identity(value):
        return value

    decorated = append_doc("Return the supplied value.")(identity)
    assert decorated is identity
    assert decorated.__doc__ == "Return the supplied value."
    assert decorated(17) == 17


def test_dotted_format_names_have_usable_property_and_method_names():
    class Formats:
        pass

    make_a_property(
        Formats,
        "custom.format",
        "Custom format",
        getter_func=lambda attribute: lambda self: attribute,
    )
    formats = Formats()
    assert formats.custom_format == "custom.format"
    assert formats.get_custom_format() == "custom.format"
    with pytest.raises(NotImplementedError, match="custom.format setter"):
        formats.set_custom_format("data")


def test_matrix_rejects_a_flat_array():
    with pytest.raises(TypeError, match="Invalid two dimensional array"):
        Matrix([1])


def test_paste_below_the_last_row_preserves_the_gap():
    matrix = Matrix([[1, 2]])
    matrix.paste((3, 1), rows=[[7, 8]])
    assert matrix.to_array() == [
        [1, 2, ""],
        ["", "", ""],
        ["", "", ""],
        ["", 7, 8],
    ]
    assert not matrix.contains(lambda row: 99 in row)


def test_uniform_normalises_none_and_pads_the_requested_shape():
    width, array = uniform([[None, 2]], min_rows=2, min_columns=3)
    assert width == 3
    assert array == [["", 2, ""], ["", "", ""]]


def test_matrix_letter_assignment_and_index_list_deletion():
    matrix = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    matrix.column["B"] = [20, 50, 80]
    assert matrix.to_array() == [[1, 20, 3], [4, 50, 6], [7, 80, 9]]
    del matrix.column[[0]]
    del matrix.row[[1]]
    assert matrix.to_array() == [[20, 3], [80, 9]]


def test_adding_streamed_rows_copies_the_original_matrix():
    from pyexcel.internal.generators import SheetStream

    matrix = Matrix([[1, 2]])
    stream = SheetStream("more", [[3, 4]])
    result = matrix.row + stream
    assert matrix.to_array() == [[1, 2]]
    assert result.to_array() == [[1, 2], [3, 4]]
    assert stream.get_internal_array() == [[3, 4]]


def test_common_row_column_addition_requires_an_implementation():
    matrix = Matrix([[1]])
    property_ = CommonPropertyAmongRowNColumn(matrix)
    with pytest.raises(NotImplementedError, match="Not implemented"):
        property_ += [[2]]


def test_common_row_column_addition_returns_its_updated_matrix():
    class AppendingRows(CommonPropertyAmongRowNColumn):
        def __iadd__(self, other):
            self._ref.extend_rows(other)
            return self

    matrix = Matrix([[1]])
    result = AppendingRows(matrix) + [[2]]
    assert result is matrix
    assert result.to_array() == [[1], [2]]
