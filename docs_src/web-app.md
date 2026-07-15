# Web app

The comparison also runs in the browser, no Python required: drop in two datasets, read the same five-category report, review a color-coded crosswalk, and download the mapping. It runs this exact package in-browser via [Pyodide](https://pyodide.org), so files never leave your device, which matters for restricted data.

Use it full-size at **<https://cstirry.github.io/field-match/>**, or right here:

<iframe
  src="https://cstirry.github.io/field-match/"
  title="field-match web app"
  style="width: 100%; height: 900px; border: 1px solid #d7dee3; border-radius: 8px;"
  loading="lazy">
</iframe>

A few notes:

- The first load fetches the Python runtime from a CDN (about 20 seconds, cached afterwards).
- Supported inputs: CSV, TSV, Excel, Parquet, JSON, Stata, SAS, and fixed-width files. SPSS and R files are not supported in-browser (their readers have no WebAssembly builds); use the Python package for those.
- Everything is processed locally in your browser tab. Reload the page to clear all data.
