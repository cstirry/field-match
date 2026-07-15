# Reading files

field-match operates on pandas DataFrames, so any way you get one works. For convenience, `compare()` accepts file paths directly, and `read_table()` opens any supported format from one path:

```python
from field_match import read_table, list_sheets

df = read_table("release_2023.parquet")
df = read_table("release_2023.xlsx", sheet_name="Data")   # default sheet_name=0 (first sheet)
list_sheets("release_2023.xlsx")   # ['Data', 'Notes', 'Codebook']

df = read_table("eavs_2018.dta")                # Stata
df = read_table("survey.sav")                   # SPSS
df = read_table("namcshc2024_sas.sas7bdat")     # SAS
df = read_table("namcshc2024_r.rds")            # R
df = read_table("layout.fwf")                   # fixed-width, columns auto-inferred
```

## Formats and what they need

| Format | Extensions | Needs |
|---|---|---|
| CSV / TSV | `.csv`, `.tsv` | nothing extra |
| JSON | `.json` | nothing extra |
| Stata | `.dta` | nothing extra |
| SAS | `.sas7bdat`, `.xpt` | nothing extra |
| Fixed-width text | `.fwf` | nothing extra |
| Excel | `.xlsx`, `.xls` | `pip install "field-match[excel]"` |
| Parquet | `.parquet` | `pip install "field-match[parquet]"` |
| SPSS | `.sav` | `pip install "field-match[spss]"` |
| R data | `.rds` | `pip install "field-match[r]"` (Python 3.10+) |

`pip install "field-match[io]"` installs everything at once. There is also `[optimal]` (scipy, for optimal assignment; see [How matching works](how-it-works.md)) and `[dev]` for contributors.

If a format's dependency is missing, the error names the exact extra to install rather than a bare library name.

## Quirks handled for you

**Non-UTF-8 text files.** Older US government releases are routinely saved as Latin-1/Windows-1252, which crashes pandas' UTF-8 default mid-file. For CSV, TSV, and fixed-width files, `read_table` retries with `encoding="latin-1"` automatically and warns that it did. Pass `encoding=` yourself and it is respected as-is, never second-guessed.

**Fixed-width layouts.** Pass `colspecs` or `widths` if you know the layout from a codebook; otherwise pandas infers column boundaries from the first 100 rows, which works for cleanly aligned files but is worth spot-checking.

**Ambiguous extensions.** `.txt` and `.dat` could be anything, so they require an explicit format:

```python
df = read_table("codes.txt", file_format="fwf", colspecs=[(0, 5), (5, 40)])
```
