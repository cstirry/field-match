# Examples with real data

Each script in [examples/](https://github.com/cstirry/field-match/tree/main/examples) downloads a real government data release and crosswalks it. Each one shows a different situation: a reused name, renames carried by content, the threshold tradeoff, and format-independence.

```bash
pip install "field-match[optimal]"
python examples/cdc_atsdr_svi.py
python examples/cdc_places.py
python examples/imls_pls.py
python examples/namcs_formats.py
```

Each script saves its files in `examples/data/` on first run; drag the same pair into the [web app](web-app.md) to see the comparison visually. The SVI example is also available as a notebook, for a step-by-step walkthrough instead of a script.

## SVI: the reused-name trap

CDC/ATSDR Social Vulnerability Index, 2010 vs. 2022 county files. As a script, [`cdc_atsdr_svi.py`](https://github.com/cstirry/field-match/blob/main/examples/cdc_atsdr_svi.py); as a notebook, [`cdc_atsdr_svi.ipynb`](https://github.com/cstirry/field-match/blob/main/examples/cdc_atsdr_svi.ipynb) ([open in Colab](https://colab.research.google.com/github/cstirry/field-match/blob/main/examples/cdc_atsdr_svi.ipynb), no install required).

- Most of the 103 columns renamed between releases.
- Two columns reused with different meanings: in 2010, `ST` held text state abbreviations and `STATE` held numeric codes; by 2022 the numeric code is called `ST`.
- A name-based merge would silently corrupt the state column.
- The content check catches it: both columns reported as suspect, true counterparts found instead (`ST` to `ST_ABBR`, `STATE` to `ST`).

## CDC PLACES: content carries the match

[`cdc_places.py`](https://github.com/cstirry/field-match/blob/main/examples/cdc_places.py): the 500 Cities project becoming PLACES in 2020.

- Renamed columns are flattened lowercase words: `cityname` vs. `locationname` scores 0 on name similarity.
- Values carry the whole match: `cityname` to `locationname`, `cityfips` to `locationid`, `populationcount` to `totalpopulation`.
- API technique demonstrated: use the reference file's own FIPS codes to request the comparable slice from the new data source, so contents genuinely overlap.

## IMLS PLS: the threshold tradeoff

[`imls_pls.py`](https://github.com/cstirry/field-match/blob/main/examples/imls_pls.py): thirty years of the Public Libraries Survey, 1992 vs. 2022.

- That much drift thins content overlap; several true renames (`LIB_NAME` to `LIBNAME`, `LIB_ADDR` to `ADDRESS`) score just under the default `match_threshold`.
- Lowering it to 0.4 recovers them, along with one wrong suggestion that review catches: the threshold tradeoff in miniature.

## NAMCS: three formats, one answer

[`namcs_formats.py`](https://github.com/cstirry/field-match/blob/main/examples/namcs_formats.py): National Ambulatory Medical Care Survey, 2022 vs. 2024, read three ways, once each from the SAS, Stata, and R releases NCHS publishes.

- All three give byte-for-byte identical results: 63 verified, 12 suspect (the `DX1`-`DX11` diagnosis codes and the `VISWT` survey weight, both genuinely drifted as the sample nearly doubled), 0 renamed, dropped, or added.
- The format the data arrived in does not change the answer.

Note: this script downloads all six files, about 590 MB total. Trim its `FORMATS` list to just the format you use.
