"""Read a data file into a DataFrame from one path, regardless of format.

Not required to use field-match - you can always load DataFrames yourself
however you like. This exists so pipeline code and the web app share one
place that knows how to open each supported format, including multi-sheet
Excel files and formats common in social-science data releases (SPSS,
Stata, fixed-width text).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

__all__ = ["read_table", "list_sheets", "SUPPORTED_EXTENSIONS"]

SUPPORTED_EXTENSIONS = (
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".parquet",
    ".json",
    ".dta",
    ".sav",
    ".fwf",
)

_FORMAT_BY_EXTENSION = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".parquet": "parquet",
    ".json": "json",
    ".dta": "stata",
    ".sav": "spss",
    ".fwf": "fwf",
}

_FILE_FORMATS = tuple(sorted(set(_FORMAT_BY_EXTENSION.values())))

# .txt/.dat could be CSV, fixed-width, or something else - no safe default.
_AMBIGUOUS_EXTENSIONS = (".txt", ".dat")


def _read_text_table(reader, path_str: str, **kwargs) -> pd.DataFrame:
    """Read a delimited/fixed-width text file, retrying on encoding failure.

    Older US government releases (pre-2000s especially) are routinely
    saved as Latin-1/Windows-1252, not UTF-8, and raise
    ``UnicodeDecodeError`` under pandas' UTF-8 default. Latin-1 maps
    every byte value to a character, so it never raises - it is the
    standard practical fallback for exactly this situation. An explicit
    ``encoding=`` kwarg is always respected as-is and never retried.
    """
    if "encoding" in kwargs:
        return reader(path_str, **kwargs)
    try:
        return reader(path_str, **kwargs)
    except UnicodeDecodeError:
        warnings.warn(
            f"{path_str!r} is not valid UTF-8; retrying with encoding='latin-1' "
            "(common in older government data). Pass encoding=... explicitly "
            "to use a different one.",
            stacklevel=3,
        )
        return reader(path_str, encoding="latin-1", **kwargs)


def list_sheets(path: str | Path) -> list[str]:
    """List sheet names in an Excel file. Returns ``[]`` for non-Excel files."""
    path = str(path)
    if not path.lower().endswith((".xlsx", ".xls")):
        return []
    with pd.ExcelFile(path) as xl:
        return list(xl.sheet_names)


def read_table(
    path: str | Path,
    sheet_name: str | int = 0,
    file_format: str | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Read a data file into a DataFrame, dispatching on file extension.

    Parameters
    ----------
    path:
        Path to a data file. Extension-recognized formats: ``.csv``,
        ``.tsv``, ``.xlsx``/``.xls`` (Excel), ``.parquet``, ``.json``,
        ``.dta`` (Stata), ``.sav`` (SPSS), ``.fwf`` (fixed-width text).
    sheet_name:
        Sheet to read for Excel files (name or 0-based index). Ignored for
        other formats. Use :func:`list_sheets` to see what's available.
    file_format:
        Override format detection - one of the values in ``_FILE_FORMATS``
        (``"csv"``, ``"excel"``, ``"fwf"``, ``"json"``, ``"parquet"``,
        ``"spss"``, ``"stata"``, ``"tsv"``). Required for ambiguous
        extensions like ``.txt``/``.dat`` that don't imply a single
        format.
    **kwargs:
        Passed through to the underlying pandas reader. For fixed-width
        files, pass ``colspecs`` or ``widths`` if you know the layout;
        otherwise pandas infers column boundaries from the first 100 rows
        (``colspecs="infer"``, the default here) - works for cleanly
        aligned files, but worth spot-checking against a codebook. For
        CSV/TSV/fixed-width files, a non-UTF-8 file (common in older
        government data) is retried automatically with ``encoding="latin-1"``
        unless you pass ``encoding=`` yourself.

    Raises
    ------
    ValueError
        If the extension isn't recognized and no ``file_format`` is
        given, or an unrecognized ``file_format`` is passed.
    ImportError
        For SPSS files, if ``pyreadstat`` isn't installed
        (``pip install "field-match[spss]"``).
    """
    path_str = str(path)
    suffix = Path(path_str).suffix.lower()
    fmt = file_format or _FORMAT_BY_EXTENSION.get(suffix)

    if fmt is None:
        hint = (
            f" {suffix!r} is ambiguous - pass file_format=... explicitly."
            if suffix in _AMBIGUOUS_EXTENSIONS
            else ""
        )
        raise ValueError(
            f"Unsupported file type {suffix!r} for {path_str!r}.{hint} "
            f"Recognized extensions: {', '.join(SUPPORTED_EXTENSIONS)}. "
            f"Supported file_format values: {', '.join(_FILE_FORMATS)}. "
            "Or load it into a DataFrame yourself and pass that in instead."
        )
    if fmt not in _FILE_FORMATS:
        raise ValueError(f"file_format must be one of {_FILE_FORMATS}, got {fmt!r}")

    if fmt == "csv":
        return _read_text_table(pd.read_csv, path_str, low_memory=False, **kwargs)
    if fmt == "tsv":
        kwargs.setdefault("sep", "\t")
        return _read_text_table(pd.read_csv, path_str, low_memory=False, **kwargs)
    if fmt == "excel":
        return pd.read_excel(path_str, sheet_name=sheet_name, **kwargs)
    if fmt == "parquet":
        return pd.read_parquet(path_str, **kwargs)
    if fmt == "json":
        return pd.read_json(path_str, **kwargs)
    if fmt == "stata":
        return pd.read_stata(path_str, **kwargs)
    if fmt == "spss":
        try:
            return pd.read_spss(path_str, **kwargs)
        except ImportError as e:
            raise ImportError(
                'Reading SPSS (.sav) files needs pyreadstat: pip install "field-match[spss]"'
            ) from e
    if fmt == "fwf":
        kwargs.setdefault("colspecs", "infer")
        return _read_text_table(pd.read_fwf, path_str, **kwargs)

    raise AssertionError(f"unhandled file_format {fmt!r}")  # pragma: no cover
