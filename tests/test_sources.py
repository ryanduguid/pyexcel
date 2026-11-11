from unittest.mock import Mock

from pyexcel import Book, Sheet
from pyexcel.source import AbstractSource
from pyexcel.plugins import FileSourceInfo
from pyexcel.plugins.sources import db_sources
from pyexcel.plugins.sources.output_to_memory import WriteSheetToMemory

from .nose_tools import raises


def test_sheet_database_adapter_forwards_default_parameters(monkeypatch):
    parser = Mock()
    renderer = Mock()
    data = {"data": [[1, 2]]}
    parser.parse_file_stream.return_value = data
    parser_factory = Mock(return_value=parser)
    renderer_factory = Mock(return_value=renderer)
    monkeypatch.setattr(db_sources.PARSER, "get_a_plugin", parser_factory)
    monkeypatch.setattr(db_sources.RENDERER, "get_a_plugin", renderer_factory)
    source = db_sources.SheetDbSource(
        "sql",
        export_columns=["a", "b"],
        parser_library="reader",
        renderer_library="writer",
        custom_option=7,
    )
    assert source.get_data() is data
    parser_factory.assert_called_once_with("sql", "reader")
    parser.parse_file_stream.assert_called_once_with(
        None, export_columns_list=[["a", "b"]], custom_option=7
    )
    sheet = Sheet([[1, 2]])
    source.write_data(sheet)
    renderer_factory.assert_called_once_with("sql", "writer")
    renderer.render_sheet_to_stream.assert_called_once_with(
        None, sheet, init=None, mapdict=None, custom_option=7
    )


def test_book_database_adapter_forwards_default_parameters(monkeypatch):
    parser = Mock()
    renderer = Mock()
    data = {"data": [[1, 2]]}
    parser.parse_file_stream.return_value = data
    monkeypatch.setattr(
        db_sources.PARSER, "get_a_plugin", Mock(return_value=parser)
    )
    monkeypatch.setattr(
        db_sources.RENDERER, "get_a_plugin", Mock(return_value=renderer)
    )
    source = db_sources.BookDbSource("sql", custom_option=7)
    assert source.get_data() is data
    parser.parse_file_stream.assert_called_once_with(None, custom_option=7)
    book = Book(data)
    source.write_data(book)
    renderer.render_book_to_stream.assert_called_once_with(
        None, book, inits=None, mapdicts=None, custom_option=7
    )


def test_source():
    source = AbstractSource(source="asource", params="params")
    info = source.get_source_info()
    assert info, (None, None)


def test_source_class_method():
    assert AbstractSource.is_my_business("read", source="asource") is True
    assert AbstractSource.is_my_business("read", file_name="asource") is False


@raises(Exception)
def test_read_only_source():
    source = AbstractSource()
    source.write_data("something")


@raises(Exception)
def test_write_only_source():
    source = AbstractSource()
    source.get_data()


@raises(Exception)
def test_write_only_sheet_source():
    source = WriteSheetToMemory()
    source.get_data()


def test_file_source_info_with_file_type():
    class CustomInfo(FileSourceInfo):
        fields = ["test"]

        def can_i_handle(self, action, file_type):
            return file_type == "csv"

    info = CustomInfo("apth")
    expected = info.is_my_business(
        "READ",
        test="unit",
        file_name="unknow.file",
        force_file_type="csv",
    )
    assert expected
