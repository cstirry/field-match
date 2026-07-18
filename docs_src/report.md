# The report

`compare()` returns a `ComparisonReport`: the crosswalk as a plain Python object. `print(report)` shows the counts; `report.summary()` adds the column names per category.

## The five categories

| Category | Meaning |
|---|---|
| `verified` | column name and contents both match |
| `renamed` | contents match, but under a different column name |
| `suspect` | column name matches, but contents do not |
| `dropped` | missing from the new dataset |
| `added` | missing from the reference dataset |

`renamed` and `suspect` are proposed from evidence rather than exact agreement, so they are generally the ones to review before applying the mapping. Whether `dropped` and `added` matter depends on whether the change was expected.

## Suspect columns

A suspect column exists under the same name on both sides, but the contents no longer line up. Each entry is a `Suspect` with:

- `name`: the shared column name
- `reason`: a plain-language explanation
- `score`: the namesake pair's own score, or `None` when the contents were not comparable

Example from the CDC Social Vulnerability Index, where `ST` and `STATE` swapped meanings between 2010 and 2022:

```
ST: contents are different types (text in the reference, numeric in the new data);
    the reference column matched 'ST_ABBR' instead; the new column matched from 'STATE' instead
```

## Applying the mapping

```python
report.mapping                 # {new_column: reference_column} for every accepted match
df = report.apply(new_data)    # copy of new_data, renamed to the reference's names
```

To review by hand first, `report.rename_snippet()` returns a pasteable dict with one commented line per decision, in the new file's own column order. Same-name matches sit in a leading comment; only actual renames go in the dict:

```python
# Matched with the same name in both files - no rename needed:
#   'fipscode'  (score=1.00, numeric)
rename_dict = {
    'locationname': 'cityname',  # score=0.91 (text)
    ...
}
# Apply with: new_df = new_df.rename(columns=rename_dict)
```

`generate_column_rename(data1, data2)` is a one-call shortcut for `compare(data1, data2).rename_snippet()`.

## The evidence

Every decision has scores behind it, and the report keeps them:

```python
report.scores                            # full evidence table: one row per compared pair
report.candidates("populationcount")     # one column's ranked candidates, best first (limit=5)
```

```
         source           target  family  name_score  content_score  score
populationcount  totalpopulation numeric        0.62          0.941  0.813
populationcount   householdcount numeric        0.55          0.760  0.676
populationcount     medianincome numeric        0.00          0.702  0.421
```

`totalpopulation` wins on the combined evidence, and the runners-up show how close the call was.

Each accepted match is a `FieldMatch` with `source`, `target`, `score`, `name_score`, `content_score`, and `family` (the inferred type the pair was compared as).

## Pipeline output

```python
report.to_dict()               # JSON-friendly: counts, categories, mapping, notes
report.suggestions             # closest below-threshold candidate for each dropped column
report.notes                   # data conditions that limited the comparison
```

Each suggestion is a `Candidate`: `column` (the dropped reference column), `candidate` (its closest column in the new data), `score`.

`notes` flags:

- **Headerless data**: no column headers, so matching used contents only.
- **Duplicate column names**: only the first occurrence of each was matched.
- **Entirely empty columns**: contents could not be checked; listed by name.

## Methods

| Method | Returns |
|---|---|
| `apply(new_df)` | copy of `new_df` renamed to the reference's names |
| `candidates(column, limit=5)` | ranked candidates for one column, as a DataFrame |
| `rename_snippet()` | pasteable rename dict, as text |
| `to_dict()` | JSON-friendly dict of the whole report |
| `summary(show_columns=True, max_columns=8)` | the report as readable text |

## Attributes

| Attribute | Type | Holds |
|---|---|---|
| `verified` | list of `FieldMatch` | same-name matches with agreeing contents |
| `renamed` | list of `FieldMatch` | matches under a different name |
| `suspect` | list of `Suspect` | same-name pairs whose contents do not line up |
| `dropped` | list of str | reference columns with no acceptable match |
| `added` | list of str | new columns nothing claimed |
| `suggestions` | list of `Candidate` | closest below-threshold candidate per dropped column |
| `matches` | list of `FieldMatch` | every accepted match |
| `mapping` | dict | `{new_column: reference_column}` |
| `scores` | DataFrame | the full evidence table |
| `notes` | list of str | warnings about the data |
| `reference_columns`, `new_columns` | list of str | all column names on each side |
| `row_counts` | tuple | (reference rows, new rows); reference is `None` for names-only |
| `match_threshold`, `verified_threshold` | float | the thresholds this report was generated with |
| `name_only` | bool | `True` if the reference was column names only |

Full signatures: [API reference](api.md).
