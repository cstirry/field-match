# Changelog

## 0.4.0

- New documentation site at https://field-match.readthedocs.io/ (MkDocs Material, sources in `docs_src/`, API reference generated from docstrings, hosted on Read the Docs). The README is now a landing page: positioning, quick start, examples, and a link into the docs.
- Report category text is plainer: dropped the "- review" suffix, and `field` -> `column` throughout to match the rest of the API (e.g. `"field name and contents both match"` is now `"column name and contents both match"`). This changes the text `print(report)` and `report.summary()` produce.
- `ComparisonReport`'s full set of methods and attributes is now documented (numpy-style docstring, rendered in the API reference and in `docs_src/report.md`); several attributes existed but were undocumented before (`matches`, `reference_columns`, `new_columns`, `row_counts`, `match_threshold`, `verified_threshold`, `name_only`).
- New example: [`cdc_atsdr_svi.ipynb`](examples/cdc_atsdr_svi.ipynb), a notebook version of the SVI example with an Open in Colab link, alongside the existing script.

## 0.3.0

- `read_table` now reads SAS (`.sas7bdat`/`.xpt`, no extra dependency needed) and R data (`.rds`, needs the new `field-match[r]` extra via `pyreadr`; requires Python 3.10+, since `pyreadr` stopped shipping a Python 3.9 wheel as of its 0.5.4 release).
- Missing-dependency errors for Excel and Parquet now name the right extra (`pip install "field-match[excel]"` / `"[parquet]"`), matching the SPSS error's existing behavior.
- New example: [namcs_formats.py](examples/namcs_formats.py) compares NAMCS 2022 vs. 2024 across SAS, Stata, and R, confirming `compare()` gives the same answer regardless of format.

## 0.2.0

Full rewrite of the 0.1.0 prototype. Breaking changes throughout.

### What's new

- **`compare(reference, new_data)`** is the main entry point. It sorts every column into one of five categories - `verified`, `renamed`, `suspect`, `dropped`, `added` - and returns a `ComparisonReport` with:
  - `print(report)` / `report.summary()` for a readable summary
  - `report.mapping` / `report.apply(df)` to rename the new data
  - `report.candidates(column)` and `report.scores` to see the evidence behind any decision
  - `report.rename_snippet()` for a reviewable, pasteable rename dict
  - `report.to_dict()` for logging and pipeline alerts
  - `report.notes` for warnings (headerless data, duplicate column names, empty columns)
- Two thresholds control the report: `match_threshold` (default 0.5, minimum score to propose a match) and `verified_threshold` (default 0.75, minimum for a same-name match to count as verified rather than suspect). All tuning parameters are keyword-only.
- `reference` accepts a DataFrame, a list of expected column names, a fitted scikit-learn model, or a file path; `new_data` accepts a DataFrame or a file path.
- `align_to_model(model, df)` fits a DataFrame to a model's `feature_names_in_`, raising a clear error on any unmatched column (or returning the report to review first with `auto_apply=False`).
- `read_table(path)` / `list_sheets(path)` read CSV, TSV, Excel, Parquet, JSON, Stata, SPSS, and fixed-width files through one function; non-UTF-8 text files (common in older government data) fall back to Latin-1 automatically.
- A drag-and-drop web app (`docs/index.html`) runs the same package in the browser via Pyodide - no Python required, files never leave the device.

### How matching works

- Each column pair is scored on name similarity (fuzzy, token-aware) and content similarity (distribution comparison for numbers and dates, value overlap for text, proportion match for booleans), blended by `name_weight`.
- Columns are compared by inferred type family, not exact dtype - `int64` matches `float64`, and numeric/date/boolean values stored as text are coerced automatically.
- Matching is one-to-one: identically named columns with agreeing contents pair up first (`exact_first`), and the rest are resolved by optimal assignment (Hungarian algorithm via `scipy`). The lower-level `match_fields` also offers a `greedy` fallback (no `scipy` needed) and an `all` mode that returns every candidate above threshold for manual review.

### Packaging

- `pyproject.toml` (hatchling), src layout, `py.typed` marker, optional extras (`[optimal]`, `[excel]`, `[parquet]`, `[spss]`, `[io]`).
- CI: Python 3.9-3.13, ruff lint/format, build verification, PyPI trusted publishing.

## 0.1.0

- Initial release.
