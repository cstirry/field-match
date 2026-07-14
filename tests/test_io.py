import pandas as pd
import pytest

from field_match import list_sheets, read_table
from field_match.io import SUPPORTED_EXTENSIONS


@pytest.fixture
def sample_df():
    return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


class TestReadTable:
    def test_csv(self, tmp_path, sample_df):
        p = tmp_path / "data.csv"
        sample_df.to_csv(p, index=False)
        pd.testing.assert_frame_equal(read_table(p), sample_df)

    def test_tsv(self, tmp_path, sample_df):
        p = tmp_path / "data.tsv"
        sample_df.to_csv(p, sep="\t", index=False)
        pd.testing.assert_frame_equal(read_table(p), sample_df)

    def test_excel_default_first_sheet(self, tmp_path, sample_df):
        p = tmp_path / "data.xlsx"
        sample_df.to_excel(p, index=False, sheet_name="Sheet1")
        pd.testing.assert_frame_equal(read_table(p), sample_df)

    def test_excel_named_sheet(self, tmp_path, sample_df):
        p = tmp_path / "data.xlsx"
        with pd.ExcelWriter(p) as writer:
            sample_df.to_excel(writer, index=False, sheet_name="First")
            sample_df.assign(a=sample_df["a"] + 10).to_excel(
                writer, index=False, sheet_name="Second"
            )
        second = read_table(p, sheet_name="Second")
        assert second["a"].tolist() == [11, 12, 13]

    def test_parquet(self, tmp_path, sample_df):
        p = tmp_path / "data.parquet"
        sample_df.to_parquet(p, index=False)
        pd.testing.assert_frame_equal(read_table(p), sample_df)

    def test_json(self, tmp_path, sample_df):
        p = tmp_path / "data.json"
        sample_df.to_json(p, orient="records")
        result = read_table(p)
        assert result["a"].tolist() == sample_df["a"].tolist()

    def test_stata(self, tmp_path, sample_df):
        p = tmp_path / "data.dta"
        sample_df.to_stata(p, write_index=False)
        result = read_table(p)
        assert result["a"].tolist() == sample_df["a"].tolist()
        assert result["b"].tolist() == sample_df["b"].tolist()

    def test_spss(self, tmp_path, sample_df):
        pyreadstat = pytest.importorskip("pyreadstat")
        p = tmp_path / "data.sav"
        pyreadstat.write_sav(sample_df, str(p))
        result = read_table(p)
        assert result["a"].tolist() == sample_df["a"].tolist()

    def test_fixed_width_with_explicit_colspecs(self, tmp_path):
        p = tmp_path / "data.fwf"
        p.write_text("VA 100\nMD 200\nDC  30\n")
        result = read_table(p, colspecs=[(0, 2), (3, 6)], header=None, names=["state", "value"])
        assert result["state"].tolist() == ["VA", "MD", "DC"]
        assert result["value"].tolist() == [100, 200, 30]

    def test_fixed_width_infers_columns_by_default(self, tmp_path):
        p = tmp_path / "data.fwf"
        p.write_text("state value\nVA    100\nMD    200\n")
        result = read_table(p)
        assert "state" in result.columns and "value" in result.columns

    def test_file_format_override(self, tmp_path, sample_df):
        # .txt is ambiguous - must pass file_format explicitly.
        p = tmp_path / "data.txt"
        sample_df.to_csv(p, index=False)
        result = read_table(p, file_format="csv")
        pd.testing.assert_frame_equal(result, sample_df)

    def test_non_utf8_csv_falls_back_to_latin1(self, tmp_path):
        # Older US government releases are routinely Latin-1/Windows-1252,
        # not UTF-8 - e.g. an accented name like "Rene\xe9" (Latin-1 for
        # "Reneé") is invalid UTF-8 and used to crash with
        # UnicodeDecodeError instead of loading.
        p = tmp_path / "data.csv"
        p.write_bytes(b"name,city\nRene\xe9,Nice\n")
        with pytest.warns(UserWarning, match="latin-1"):
            result = read_table(p)
        assert result["name"].tolist() == ["Reneé"]

    def test_explicit_encoding_is_respected_not_retried(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_bytes(b"name,city\nRene\xe9,Nice\n")
        with pytest.raises(UnicodeDecodeError):
            read_table(p, encoding="utf-8")

    def test_ambiguous_extension_without_format_raises(self, tmp_path, sample_df):
        p = tmp_path / "data.txt"
        sample_df.to_csv(p, index=False)
        with pytest.raises(ValueError, match="ambiguous"):
            read_table(p)

    def test_invalid_file_format_raises(self, tmp_path, sample_df):
        p = tmp_path / "data.csv"
        sample_df.to_csv(p, index=False)
        with pytest.raises(ValueError, match="file_format must be one of"):
            read_table(p, file_format="bogus")

    def test_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "data.xyz"
        p.write_text("nonsense")
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_table(p)

    def test_supported_extensions_documented(self):
        for ext in (".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".dta", ".sav", ".fwf"):
            assert ext in SUPPORTED_EXTENSIONS


class TestListSheets:
    def test_lists_all_sheets(self, tmp_path, sample_df):
        p = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(p) as writer:
            sample_df.to_excel(writer, index=False, sheet_name="Alpha")
            sample_df.to_excel(writer, index=False, sheet_name="Beta")
        assert list_sheets(p) == ["Alpha", "Beta"]

    def test_non_excel_returns_empty(self, tmp_path, sample_df):
        p = tmp_path / "data.csv"
        sample_df.to_csv(p, index=False)
        assert list_sheets(p) == []
