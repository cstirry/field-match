# Web app

Runs in the browser, no Python required: drop in two datasets, get the same five-category report, review a color-coded crosswalk, download the mapping. Runs this exact package in-browser via [Pyodide](https://pyodide.org); files never leave your device.

Use it full-size at **<https://cstirry.github.io/field-match/>**, or right here:

<iframe
  src="https://cstirry.github.io/field-match/"
  title="field-match web app"
  style="width: 100%; height: 900px; border: 1px solid #d7dee3; border-radius: 8px;"
  loading="lazy">
</iframe>

- First load fetches the Python runtime from a CDN: about 20 seconds, cached afterwards.
- Supported inputs: CSV, TSV, Excel, Parquet, JSON, Stata, SAS, fixed-width. SPSS and R not supported in-browser (no WebAssembly build for their readers); use the Python package for those.
- Everything processed locally in the browser tab. Reload the page to clear all data.
