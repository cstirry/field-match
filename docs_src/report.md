# The report

`compare()` returns a `ComparisonReport`: a plain Python object holding the structured results, which also knows how to print itself. `print(report)` shows the counts; `report.summary()` adds the column names in each category.

## The five categories

Every column lands in exactly one pile:

| Category | Meaning | Needs action? |
|---|---|---|
| `verified` | field name and contents both match | No. Safe to ignore. |
| `renamed` | contents match, but under a different field name | Review the proposed mapping. |
| `suspect` | field name matches, but contents do not | Yes, check these first. |
| `dropped` | reference column missing from the new dataset | Decide: really gone, or lower the threshold? |
| `added` | new dataset column is not in the reference dataset | Decide: keep or ignore. |

**Suspect is the pile that earns its keep.** It holds names that exist on both sides but no longer mean the same thing. A real case from the CDC's Social Vulnerability Index: in 2010, `ST` held text state abbreviations and `STATE` held numeric codes; by 2022 the numeric code was called `ST`. Matching by name alone would silently merge codes into abbreviations. field-match checks the contents, refuses the name-only pairing, and reports:

```
ST: contents are different types (text in the reference, numeric in the new data);
    the reference column matched 'ST_ABBR' instead; the new column matched from 'STATE' instead
```

Each suspect entry carries a plain-language `reason` like that one, plus the pair's score when the contents were comparable.

## Acting on the report

```python
report.mapping                 # {new_column: reference_column} for every accepted match
df = report.apply(new_data)    # rename the new data to the reference's names
```

Prefer to hand-check before renaming? `report.rename_snippet()` writes a pasteable snippet with one commented line per decision, in the new file's own column order. Same-name matches sit in a leading comment (verified, nothing to rename); only actual renames go in the dict:

```python
# Matched with the same name in both files - no rename needed:
#   'FIPS'  (score=1.00, numeric)
rename_dict = {
    'EPL_AGE65': 'PL_AGE65',  # score=0.94 (numeric)
    ...
}
# Apply with: new_df = new_df.rename(columns=rename_dict)
```

## Digging into the evidence

Every decision has scores behind it, and the report keeps them:

```python
report.scores                  # the full evidence table: one row per compared pair
report.candidates("E_POV")     # one column's ranked candidates, best first
```

`candidates` is the drill-down for "why did it pick that?". From the SVI example:

```
source   target  family  name_score  content_score  score
 E_POV E_POV150 numeric         0.9          0.829  0.857
 E_POV E_DISABL numeric         0.5          0.953  0.772
 E_POV  E_AGE65 numeric         0.5          0.899  0.739
```

`E_POV150` wins on the combination of name and content evidence, and you can see exactly how close the runners-up were.

## For pipelines

```python
report.to_dict()               # JSON-friendly: counts, categories, mapping, notes
report.suggestions             # closest below-threshold candidate for each dropped column
report.notes                   # warnings worth knowing about (see below)
```

`notes` flags conditions that affect how much the report can verify:

- **Headerless data**: if a file has no column headers (pandas numbers them), matching switches to contents only and the report says so.
- **Duplicate column names**: only the first occurrence of each is matched; noted.
- **Entirely empty columns**: their contents cannot be checked; listed by name.
