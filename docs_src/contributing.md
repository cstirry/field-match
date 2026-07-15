# Contributing

Development setup, testing, the release process, and web app hosting details live in [CONTRIBUTING.md](https://github.com/cstirry/field-match/blob/main/CONTRIBUTING.md) in the repository.

The short version:

```bash
git clone https://github.com/cstirry/field-match.git
cd field-match
pip install -e ".[dev]"
pytest                  # run the test suite
ruff check .            # lint
ruff format --check .   # formatting
```

## Working on these docs

The documentation sources are Markdown files in `docs_src/` (the `docs/` folder serves the web app on GitHub Pages, so the name differs from the usual convention). To preview locally:

```bash
pip install -r docs_src/requirements.txt
mkdocs serve
```

Then open <http://127.0.0.1:8000>. Read the Docs rebuilds the published site automatically on every push to `main`.
