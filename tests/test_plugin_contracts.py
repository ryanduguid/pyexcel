from unittest.mock import Mock

import pytest
import pyexcel as pe
from pyexcel import constants, exceptions
from pyexcel.plugins import (
    PARSER,
    RENDERER,
    SourceInfo,
    IOPluginInfo,
    FileSourceInfo,
    InputSourceInfo,
    OutputSourceInfo,
    find_file_type_from_file_name,
)
from pyexcel.internal import SOURCE
from pyexcel.internal.attributes import register_sheet_attribute


def test_source_library_selection_is_separate_from_the_io_library(monkeypatch):
    class RecordingSource:
        def __init__(self, **keywords):
            self.keywords = keywords

    loader = Mock(return_value=RecordingSource)
    monkeypatch.setattr(SOURCE, "load_me_now", loader)
    source = SOURCE.get_source(
        source_library="source-addon", library="io-addon", file_type="csv"
    )
    loader.assert_called_once_with(
        "sheet-read", action="read", library="source-addon", file_type="csv"
    )
    assert source.keywords == {"file_type": "csv", "library": "io-addon"}


def test_unknown_source_target_is_rejected():
    info = SourceInfo(
        "unloaded.source",
        targets=("unknown",),
        actions=(constants.READ_ACTION,),
        attributes=["csv"],
        key="file_type",
    )
    with pytest.raises(Exception, match="Known target: unknown"):
        SOURCE._register_a_plugin_info(info)


def test_unsupported_file_type_is_reported():
    with pytest.raises(exceptions.FileTypeNotSupported, match="not-a-format"):
        pe.get_sheet(file_type="not-a-format", file_content="data")


def test_unknown_parameter_diagnostic_omits_the_on_demand_option():
    with pytest.raises(exceptions.UnknownParameters) as raised:
        pe.get_sheet(on_demand=True, unknown_parameter=1)
    message = str(raised.value)
    assert "unknown_parameter" in message
    assert "on_demand" not in message


def test_missing_source_parameters_are_reported():
    with pytest.raises(
        exceptions.UnknownParameters, match="No parameters found!"
    ):
        SOURCE.get_source()


def test_file_source_requires_a_capability_implementation():
    info = FileSourceInfo("unloaded.source", fields=["file_type"])
    with pytest.raises(NotImplementedError):
        info.is_my_business(constants.READ_ACTION, file_type="csv")


def test_input_and_output_descriptors_reject_the_opposite_action():
    assert not InputSourceInfo("unloaded.source").can_i_handle(
        constants.WRITE_ACTION, "csv"
    )
    assert not OutputSourceInfo("unloaded.source").can_i_handle(
        constants.READ_ACTION, "csv"
    )


@pytest.mark.parametrize(
    "action,manager", [("read", PARSER), ("write", RENDERER)]
)
def test_file_type_selection_uses_the_longest_matching_suffix(
    monkeypatch, action, manager
):
    monkeypatch.setattr(
        manager, "get_all_file_types", lambda: ["gz", "csv.gz"]
    )
    assert find_file_type_from_file_name("report.CSV.GZ", action) == "csv.gz"


def test_plugin_file_types_can_be_computed_when_tags_are_requested():
    info = IOPluginInfo(
        "parser", "unloaded.Parser", file_types=lambda: ["csv", "tsv"]
    )
    assert list(info.tags()) == ["csv", "tsv"]


def test_repeated_format_registration_preserves_the_combined_property():
    original = pe.Sheet.csv
    register_sheet_attribute(constants.SHEET, constants.READ_ACTION, "csv")
    register_sheet_attribute(constants.SHEET, constants.WRITE_ACTION, "csv")
    assert pe.Sheet.csv is original
    sheet = pe.Sheet()
    sheet.csv = "1,2\n"
    assert sheet.get_internal_array() == [[1, 2]]
    assert sheet.csv == "1,2\r\n"
