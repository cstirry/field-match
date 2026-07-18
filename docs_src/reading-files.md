# Reading files

field-match operates on pandas DataFrames; any way you get one works. `compare()` also accepts file paths directly, and `read_table()` opens any supported format from one path:

```python
from field_match import read_table, list_sheets

df = read_table("release_2023.parquet")
df = read_table("release_2023.xlsx", sheet_name="Data")   # default sheet_name=0 (first sheet)
list_sheets("release_2023.xlsx")   # ['Data', 'Notes', 'Codebook']; [] for non-Excel files

df = read_table("eavs_2018.dta")                # Stata
df = read_table("survey.sav")                   # SPSS
df = read_table("namcshc2024_sas.sas7bdat")     # SAS
df = read_table("namcshc2024_r.rds")            # R
df = read_table("layout.fwf")                   # fixed-width, columns auto-inferred
```

Extra keyword arguments pass through to the underlying pandas reader, so anything `pd.read_csv`, `pd.read_excel`, etc. accept works here too.

## Formats

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

- `pip install "field-match[io]"` installs all of the above at once.
- `[optimal]`: scipy, for optimal assignment (see [How matching works](how-it-works.md)). `[dev]`: for contributors.
- If a format's dependency is missing, the error names the exact extra to install.

## Encoding, layouts, and ambiguous extensions

- **Non-UTF-8 text files**: older US government releases are often Latin-1/Windows-1252. For CSV, TSV, and fixed-width files, `read_table` retries with `encoding="latin-1"` automatically and warns that it did. Pass `encoding=` yourself and it is used as-is.
- **Fixed-width layouts**: pass `colspecs` or `widths` if known from a codebook. Otherwise pandas infers column boundaries from the first 100 rows; fine for cleanly aligned files, worth spot-checking.
- **Ambiguous extensions**: `.txt` and `.dat` do not imply a format, so pass `file_format` explicitly (`"csv"`, `"tsv"`, `"fwf"`, `"json"`, `"excel"`, `"parquet"`, `"stata"`, `"spss"`, `"sas"`, or `"rds"`):

```python
df = read_table("codes.txt", file_format="fwf", colspecs=[(0, 5), (5, 40)])
```
