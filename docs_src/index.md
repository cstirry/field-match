# Getting started

field-match builds a column crosswalk between two dataset versions: it compares every column pair on name *and* content, then reports which columns still match, which appear renamed, which share a name but no longer match in content, and which were added or dropped. Because the matching considers contents as well as names, a rename is identified even without a codebook.

Developed for recurring public-interest data releases (CDC SVI, PLACES, NAMCS, IMLS PLS), where column drift is common.

No Python? Try the [web app](web-app.md) instead. Drop in two files, nothing to install.

## Install

```bash
pip install field-match
```

- CSV, TSV, JSON, Stata, SAS, fixed-width: no extra install.
- Other formats: one optional extra each, see [Reading files](reading-files.md).

## First comparison

```python
from field_match import compare, read_table

new_data = read_table("survey_2022.xlsx")
report = compare("survey_2021.csv", new_data)
print(report)
```

```
field-match comparison: 103 reference columns vs 158 new columns
(3,143 vs 3,144 rows; match_threshold 0.50, verified_threshold 0.75)

  16  verified  column name and contents both match
  64  renamed   contents match, but under a different column name
   4  suspect   column name matches, but contents do not
  21  dropped   missing from the new dataset
  76  added     missing from the reference dataset
```

Every column lands in exactly one category. `renamed` and `suspect` are generally the ones to review before applying the mapping. Details: [The report](report.md).

```python
report.summary()                    # the same report, with column names listed
report.candidates("population")     # ranked candidates for one column, with scores
df = report.apply(new_data)         # rename the new data to the reference's names
```

## What `compare()` accepts

`compare(reference, new_data)`. `new_data` is a DataFrame or a file path. `reference` can be:

| Reference | What gets checked |
|---|---|
| a previous dataset (DataFrame or file path) | names and contents |
| a list of expected column names | names only; the report notes contents were not checked |
| a fitted scikit-learn model | names only, against the model's `feature_names_in_` |

## Aligning to a model

```python
from field_match import align_to_model

aligned = align_to_model(model, new_df)   # raises if any expected column has no match
predictions = model.predict(aligned)
```

Pass `auto_apply=False` to get the `ComparisonReport` to review instead of a ready-to-predict DataFrame.

## Checking a pipeline

```python
report = compare(last_clean_release, incoming)
log.info(report.to_dict())               # JSON-friendly, for structured logs
if report.suspect or report.dropped:
    alert(report.summary())              # a human decides
else:
    df = report.apply(incoming)
```

## Scope

- The reference dataset is the expectation: its column names, types, and values are checked directly. No schema or rules to write.
- field-match answers which column is which, and whether a column's meaning changed.
- It does not check value-level rules like "no nulls" or "between 0 and 1". Use a validation library for those, after the columns are aligned.

## Next

- [The report](report.md): the five categories and the report object in full.
- [Tuning](tuning.md): the two thresholds and the name/content weight.
- [Examples](examples.md): four walkthroughs on real government data releases.
