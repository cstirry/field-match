# field-match

[![PyPI](https://img.shields.io/pypi/v/field-match)](https://pypi.org/project/field-match/)
[![CI](https://github.com/cstirry/field-match/actions/workflows/ci.yml/badge.svg)](https://github.com/cstirry/field-match/actions)
[![Docs](https://readthedocs.org/projects/field-match/badge/?version=latest)](https://field-match.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Names, types, and values can all shift between data releases, quietly breaking anything downstream that assumes a stable schema. `field-match` compares a dataset against a reference dataset and builds a column crosswalk, reporting which columns still match on name and content, which appear renamed, which share a name but no longer match in content, and which were added or dropped. Matching considers column contents as well as names, so a rename is identified even without a codebook.

Unlike other libraries in the data validation and data quality ecosystem, field-match answers the earlier question of which column is which. Some tools diff values once you know the mapping; others require you to write out rules. field-match instead uses your last clean release as the reference. It works across numeric, datetime, boolean, and text columns, reads CSV, Stata, SAS, and fixed-width files with no extra dependencies, plus Excel, Parquet, SPSS, and R via optional extras, and a browser-based version (no install) runs the same matching in-browser via Pyodide.

Developed for recurring public-interest data releases, where column drift is common.

No Python? Try the web app: **https://cstirry.github.io/field-match/**. Drop in two files, nothing to install.

## Quick start

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

Review the proposed mapping, then apply it: `df = report.apply(new_data)`. The reference can be a previous dataset, a list of expected column names, or a fitted sklearn model.

**[Full documentation](https://field-match.readthedocs.io/)**: the report in depth, supported file formats, tuning, how matching works, and the API reference.

## Examples with real data

Four scripts in [examples/](examples) download real government releases and crosswalk them: the CDC/ATSDR Social Vulnerability Index (a reused-name trap), CDC 500 Cities/PLACES (renames recovered on content alone), the IMLS Public Libraries Survey (thirty years of drift), and NAMCS (identical results across SAS, Stata, and R). Walkthroughs in the [docs](https://field-match.readthedocs.io/examples/).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, docs, and the release process.

## License

MIT; see [LICENSE](LICENSE).
