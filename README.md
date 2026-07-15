# field-match

[![PyPI](https://img.shields.io/pypi/v/field-match)](https://pypi.org/project/field-match/)
[![CI](https://github.com/cstirry/field-match/actions/workflows/ci.yml/badge.svg)](https://github.com/cstirry/field-match/actions)
[![Docs](https://readthedocs.org/projects/field-match/badge/?version=latest)](https://field-match.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A new release of a dataset you depend on just arrived. Before it breaks last year's analysis, your data pipeline, or your model, field-match shows you in seconds what likely changed: which columns kept their meaning, which were renamed, which changed under the same name, and which were dropped or added. It judges by the values as well as the names, so you don't have to dig through codebooks. Built with annual public interest data releases in mind.

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

## How it relates to tools you may know

- **Great Expectations, pandera** validate data against rules you write and maintain. field-match needs no rules: your last clean release is the expectation suite, and instead of just failing on a missing column, it proposes what happened to it.
- **datacompy, pandas `DataFrame.compare`** diff values once you know which column maps to which. field-match answers the question that comes first: which column *is* which.
- **splink, recordlinkage** match rows (people, records). field-match matches columns.
- **Valentine** benchmarks academic schema-matching algorithms. field-match is the practitioner workflow: one call, a categorical report, review, apply.

## Examples with real data

Four scripts in [examples/](examples) download real government releases and crosswalk them: the CDC/ATSDR Social Vulnerability Index (a reused-name trap), CDC 500 Cities/PLACES (renames recovered on content alone), the IMLS Public Libraries Survey (thirty years of drift), and NAMCS (identical results across SAS, Stata, and R). Walkthroughs in the [docs](https://field-match.readthedocs.io/examples/).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, docs, and the release process.

## License

MIT; see [LICENSE](LICENSE).
