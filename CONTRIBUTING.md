# Contributing

## Development setup

```bash
git clone https://github.com/cstirry/field-match.git
cd field-match
pip install -e ".[dev]"
pytest                  # run the test suite
ruff check .            # lint
ruff format --check .   # formatting
```

CI runs the same checks on Python 3.9 through 3.13, plus a build
verification (`python -m build && twine check dist/*`).

## Web app hosting

The web app in `docs/` is served by GitHub Pages, configured once in the
repo: **Settings → Pages → Source: Deploy from a branch → `main` /
`docs`**. Every merge to `main` that touches `docs/` redeploys the site
at https://cstirry.github.io/field-match/ automatically.

The page installs the package from the wheel file in `docs/`, so code
changes only reach the site after rebuilding it (step 2 of the release
checklist below).

## Releasing

The version lives in one place: `__version__` in
[src/field_match/__init__.py](src/field_match/__init__.py)
(`pyproject.toml` reads it from there at build time). To cut a release:

1. Bump `__version__` and add a [CHANGELOG.md](CHANGELOG.md) entry.
2. Rebuild the web app's wheel and update the filename it installs:

   ```bash
   python -m build && cp dist/field_match-*.whl docs/
   ```

   then update the wheel filename in `docs/index.html` (the `whl`
   constant in the boot script) and delete the old wheel from `docs/`.
3. Merge to `main`, then create a GitHub release tagged `vX.Y.Z`. The
   publish workflow builds and uploads to PyPI automatically via
   trusted publishing.
