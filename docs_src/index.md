# Getting started

A new release of a dataset you depend on just arrived. Before it breaks last year's analysis, your data pipeline, or your model, field-match shows you in seconds what likely changed: which columns kept their meaning, which were renamed, which changed under the same name, and which were dropped or added. It judges by the values as well as the names, so you don't have to dig through codebooks. Built with annual public interest data releases in mind.

No Python? Try the [web app](web-app.md) instead. Drop in two files, nothing to install.

## Install

```bash
pip install field-match
```

That covers CSV, TSV, JSON, Stata, SAS, and fixed-width files out of the box. Other formats need one optional extra each; see [Reading files](reading-files.md).

## First comparison

One function does the work. Pass it a reference dataset (usually your last clean release) and the new one, as DataFrames or as file paths:

```python
from field_match import compare

report = compare("survey_2021.csv", "survey_2022.xlsx")
print(report)
```

```
field-match comparison: 103 reference columns vs 158 new columns
(3,143 vs 3,144 rows; match_threshold 0.50, verified_threshold 0.75)

  16  verified  field name and contents both match
  64  renamed   contents match, but under a different field name - review
   4  suspect   field name matches, but contents do not - review
  21  dropped   reference column missing from the new dataset
  76  added     new dataset column is not in the reference dataset
```

Every column lands in exactly one of those five piles. `verified` is safe to ignore; `suspect` is the one to check first. [The report](report.md) explains each category and everything else the report object can do, including applying the rename mapping once you are satisfied:

```python
report.summary()               # the same report, with column names listed
report.candidates("E_POV")     # ranked candidates for one column, with scores
df = report.apply(new_data)    # rename the new data to the reference's names
```

## The reference can be more than a dataset

`compare(reference, new_data)` accepts whatever you have as the reference:

- **A previous dataset** (DataFrame or file path). Names and contents both get checked. This is the strongest mode.
- **A list of expected column names**, e.g. from a pipeline config. Names only; the report notes that contents were not checked.
- **A fitted scikit-learn model.** Its `feature_names_in_` becomes the expected schema. The `align_to_model` convenience wraps this and returns a ready-to-predict DataFrame:

```python
from field_match import align_to_model

aligned = align_to_model(model, new_df)   # raises, loudly, on unmatched columns
predictions = model.predict(aligned)
```

## Guarding a pipeline

The report is built for logging and alerting, so drift gets caught before it corrupts a series:

```python
report = compare(last_clean_release, incoming)
log.info(report.to_dict())               # JSON-friendly, for structured logs
if report.suspect or report.dropped:
    alert(report.summary())              # a human decides
else:
    df = report.apply(incoming)
```

## Where to next

- [Why field-match](why.md): what it does that validation and diff tools don't.
- [The report](report.md): the five categories and the report object in full.
- [Tuning](tuning.md): the two thresholds and the name/content weight.
- [Examples](examples.md): four walkthroughs on real government data releases.
