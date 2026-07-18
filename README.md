# field-match

[![Web app](https://img.shields.io/badge/web_app-try_it-teal)](https://cstirry.github.io/field-match/)
[![PyPI](https://img.shields.io/pypi/v/field-match)](https://pypi.org/project/field-match/)
[![CI](https://github.com/cstirry/field-match/actions/workflows/ci.yml/badge.svg)](https://github.com/cstirry/field-match/actions)
[![Docs](https://readthedocs.org/projects/field-match/badge/?version=latest)](https://field-match.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Names, types, and values can all shift between data releases, quietly breaking anything downstream that assumes a stable schema. `field-match` builds a column crosswalk between two dataset versions: it compares every column pair on name *and* content, then reports which columns still match (**verified**), which appear **renamed**, which share a name but no longer match in content (**suspect**), and which were **added** or **dropped**.

The alternative is checking column by column, by hand and against documentation that may be buried. `field-match` makes that first pass in one call and flags what needs review.

Unlike other libraries in the data validation and data quality ecosystem, `field-match` builds the crosswalk itself rather than assuming you already have one. Some tools diff values once you know the mapping; others require you to write the mapping out as rules. `field-match` instead treats your last clean release as the reference and works the mapping out from name and content matching. It works across numeric, datetime, boolean, and text columns, reads CSV, Stata, SAS, and fixed-width files with no extra dependencies, plus Excel, Parquet, SPSS, and R via optional extras, and a browser-based version (no install) runs the same matching in-browser via Pyodide.

Developed for recurring public-interest data releases, where column drift is common.

No Python? Try the web app: **https://cstirry.github.io/field-match/**. Drop in two files, nothing to install.

## Quick start

```bash
pip install field-match
```

```python
from field_match import compare, read_table

new_data = read_table("survey_2022.xlsx")
report = compare("survey_2021.csv", new_data)
print(report)
```

```
  16  verified  column name and contents both match
  64  renamed   contents match, but under a different column name
   4  suspect   column name matches, but contents do not
  21  dropped   missing from the new dataset
  76  added     missing from the reference dataset
```

Review the proposed mapping, then apply it: `df = report.apply(new_data)`. The reference can be a previous dataset, a list of expected column names, or a fitted sklearn model.

**[Full documentation](https://field-match.readthedocs.io/)**: the report in depth, supported file formats, tuning, how matching works, and the API reference.

## Examples with real data

Four scripts in [examples/](examples) download real government releases and crosswalk them to identify column drift:

1. [CDC/ATSDR Social Vulnerability Index](https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html) ([`cdc_atsdr_svi.py`](examples/cdc_atsdr_svi.py), or as a notebook: [`cdc_atsdr_svi.ipynb`](examples/cdc_atsdr_svi.ipynb) / [Colab](https://colab.research.google.com/github/cstirry/field-match/blob/main/examples/cdc_atsdr_svi.ipynb)): column name reused differently
2. [CDC 500 Cities/PLACES](https://data.cdc.gov/browse?category=500+Cities+%26+Places) ([`cdc_places.py`](examples/cdc_places.py)): column renames identified by content
3. [IMLS Public Libraries Survey](https://www.imls.gov/research-evaluation/surveys/public-libraries-survey-pls) ([`imls_pls.py`](examples/imls_pls.py)): thirty years of column drift
4. [NAMCS](https://www.cdc.gov/nchs/namcs/documentation/about-the-data-2024.html) ([`namcs_formats.py`](examples/namcs_formats.py)): SAS, Stata, and R datasets

Walkthroughs in the [docs](https://field-match.readthedocs.io/examples/).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, docs, and the release process.

## License

MIT; see [LICENSE](LICENSE).
