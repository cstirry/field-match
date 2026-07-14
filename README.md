# field-match

[![PyPI](https://img.shields.io/pypi/v/field-match)](https://pypi.org/project/field-match/)
[![CI](https://github.com/cstirry/field-match/actions/workflows/ci.yml/badge.svg)](https://github.com/cstirry/field-match/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Match columns between dataset versions by comparing column names *and* column contents.

No Python? Try the web app: **https://cstirry.github.io/field-match/**. Drop in two files, nothing to install.

```bash
pip install field-match
```

```python
from field_match import compare

report = compare("survey_2021.csv", "survey_2022.xlsx")
print(report)
```

```
  16  verified  field name and contents both match
  64  renamed   contents match, but under a different field name - review
   4  suspect   field name matches, but contents do not - review
  21  dropped   reference column missing from the new dataset
  76  added     new dataset column is not in the reference dataset
```

## Why

Names, types, and values can all shift between data releases, quietly breaking anything downstream that expects a stable schema. `field-match` compares a new dataset against a reference on both column names *and* contents, then sorts every column into verified, renamed, suspect, dropped, or added, so there's less to check by hand.

What sets it apart from other comparison tools is that it doesn't assume columns line up by name. It scores every pair on name similarity *and* content similarity, so a column can still be matched after it's been renamed. That's especially useful for the annual data releases common with public-interest datasets.

## How columns are matched

Each column pair is scored on two things: the column names (word-aware fuzzy matching, so `CustomerID`, `customer_id`, and `id_customer` all agree) and the column contents, compared in a way that suits the data type (distributions for numbers and dates, share of yes-values for booleans, value overlap for text). The two scores are blended by `name_weight` (see [Tuning](#tuning)) into one 0-1 score, and columns are paired one-to-one so no two claim the same match.

## Installation

```bash
pip install field-match
# optional extras:
pip install "field-match[optimal]"   # scipy, for optimal assignment
pip install "field-match[excel]"     # openpyxl, for Excel files
pip install "field-match[parquet]"   # pyarrow, for Parquet files
pip install "field-match[spss]"      # pyreadstat, for SPSS files
pip install "field-match[io]"        # excel + parquet + spss (Stata and fixed-width need no extra)
```

### Reading files

`field-match` operates on DataFrames, so any way you get one works (e.g. `pd.read_csv`, etc.). `read_table` is a small convenience to support the web app that dispatches on file extension. Recognized extensions: CSV, TSV, Excel, Parquet, JSON, Stata (`.dta`), SPSS (`.sav`), fixed-width (`.fwf`).

```python
from field_match import read_table, list_sheets

df = read_table("release_2023.parquet")
df = read_table("release_2023.xlsx", sheet_name="Data")   # default sheet_name=0 (first sheet)
list_sheets("release_2023.xlsx")   # ['Data', 'Notes', 'Codebook']

df = read_table("eavs_2018.dta")                          # Stata
df = read_table("survey.sav")                             # SPSS - needs `field-match[spss]`
df = read_table("layout.fwf")                              # fixed-width, columns auto-inferred by default
```

Ambiguous extensions like `.txt`/`.dat` need an explicit `file_format`:

```python
df = read_table("codes.txt", file_format="fwf", colspecs=[(0, 5), (5, 40)])
```

## Usage

One function does the work: `compare(reference, new_data)`. The reference can be a previous dataset (names *and* contents get checked), a list of expected column names (names only), or a fitted sklearn model. Both arguments also accept file paths.

### Compare two datasets

The report above is what `compare()` returns. `report.summary()` adds the column names in each category, and every category is a plain Python attribute so code can act on it directly:

```python
report.verified, report.renamed, report.suspect, report.dropped, report.added

report.candidates("Col_Name")     # ranked candidates for one column, with scores
report.mapping                    # {new_name: reference_name}
df = report.apply(new_data)       # rename the new data to the reference's names
```

The suspect pile is the one to check first. It holds columns that exist on both sides but no longer mean the same thing, like a column whose values changed type between releases.

Prefer to hand-check before renaming? `report.rename_snippet()` (or the `generate_column_rename()` convenience) writes a pasteable snippet with one commented line per decision. A drag-and-drop web version of all of this is included too; see [Web app](#web-app-no-python-required).

### Guard a data pipeline

You want to know a new release drifted *before* it corrupts a series. The report is built for logging and alerting:

```python
report = compare(last_clean_release, incoming)
log.info(report.to_dict())               # JSON-friendly, for structured logs
if report.suspect or report.dropped:
    alert(report.summary())              # a human decides
else:
    df = report.apply(incoming)
```

With only a schema to compare against (no reference values), pass the expected names: `compare(["fipscode", "state", "county"], incoming)`. The report will note that contents were not checked.

### Fit new data to a saved model

A pickled sklearn model fails on `predict()` if the new data's column names drifted from training. `align_to_model` uses the model's `feature_names_in_` as the expected schema and returns a ready-to-predict DataFrame:

```python
import pickle
from field_match import align_to_model

model = pickle.load(open("income_model.pkl", "rb"))
aligned = align_to_model(model, new_df)   # raises, loudly, on unmatched columns
predictions = model.predict(aligned)
```

Pass `auto_apply=False` to get the `ComparisonReport` to review instead.

### Tuning

All tuning parameters are optional and keyword-only (pass them by name).

| Parameter | Range | Default | Meaning |
|---|---|---|---|
| `match_threshold` | 0-1 | 0.5 | minimum score to propose a match; higher = fewer, more confident matches |
| `verified_threshold` | 0-1 | 0.75 | minimum score for a same-name match to count as verified instead of suspect |
| `name_weight` | 0-1 | 0.4 | 0 = judge only by values (auto for headerless files), 1 = judge only by names |
| `sample_size` | rows | 2000 | files longer than this are sampled before content comparison |
| `exact_first` | bool | True | pair identically named, same-type columns immediately, skipping the expensive comparison |

## Under the hood

`compare()` runs in three stages, each public for custom logic:

1. **Exact names first** (`exact_first`): identically named columns with agreeing contents pair up immediately.
2. **Scoring**: every remaining pair gets a name score and a content score, blended by `name_weight`. Standalone via `similarity_scores(df1, df2)`.
3. **Assignment**: `match_fields(df1, df2)` resolves the one-to-one pairing. `assignment` picks the strategy: `"optimal"` (default, Hungarian algorithm, needs `scipy`), `"greedy"` (no extra dependency), or `"all"` (every candidate above `match_threshold`, unresolved).

The five scoring functions are importable too: `name_similarity`, `numeric_similarity`, `datetime_similarity`, `boolean_similarity`, `text_similarity`. Each takes two Series and returns a score in [0, 1].

## Limitations

Content matching keys on the *shape* of a column's values, not their meaning. Numeric and datetime columns are compared by distribution (a KS statistic, raw and median-centered), so two unrelated columns with similar distributions, say any two roughly-normal columns on comparable scales, can score high on content alone. One-to-one assignment and `name_weight` keep this in check in practice, but a match that rests on contents while scoring ~0 on the name is exactly the kind to eyeball. That is what the `renamed` and `suspect` piles, and `report.candidates(column)`, are for: review before you `apply()`.

## Examples with real data

Each script in [examples/](examples) downloads a real government data release and crosswalks it:

- [cdc_atsdr_svi.py](examples/cdc_atsdr_svi.py) - CDC/ATSDR Social Vulnerability Index, 2010 vs. 2022. Catches the `ST`/`STATE` reused-name trap, where both names exist in both files but swapped meaning.
- [cdc_places.py](examples/cdc_places.py) - CDC 500 Cities / PLACES, 2019 vs. 2020. Identifies column renmaing like `cityname` → `locationname` and `populationcount` → `totalpopulation` based on content.
- [imls_pls.py](examples/imls_pls.py) - IMLS Public Libraries Survey, 1992 vs. 2022.

```bash
pip install "field-match[optimal]"
python examples/cdc_atsdr_svi.py
python examples/cdc_places.py
python examples/imls_pls.py
```

Each script saves its two files in `examples/data/` the first time it runs, so you can also drag that same pair into the web app to see the comparison visually.

## Web app (no Python required)

Try the comparison in your browser: **https://cstirry.github.io/field-match/**

Drop in two files, get the same five-category report, review the color-coded crosswalk, and download the mapping. It runs this exact package in-browser via [Pyodide](https://pyodide.org), so files never leave your device.

To run it from a local checkout instead: `python -m http.server -d docs`, then open http://localhost:8000 (opening the file directly won't work; Pyodide needs HTTP). Hosting details are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the release process.

## License

MIT; see [LICENSE](LICENSE).
