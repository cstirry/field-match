# Contributing

Development setup, testing, the release process, and web app hosting: [CONTRIBUTING.md](https://github.com/cstirry/field-match/blob/main/CONTRIBUTING.md) in the repository.

```bash
git clone https://github.com/cstirry/field-match.git
cd field-match
pip install -e ".[dev]"
pytest                  # run the test suite
ruff check .            # lint
ruff format --check .   # formatting
```

## Working on these docs

Sources: Markdown files in `docs_src/` (`docs/` serves the web app on GitHub Pages, hence the different name). Preview locally:

```bash
pip install -r docs_src/requirements.txt
mkdocs serve
```

Open <http://127.0.0.1:8000>. Read the Docs rebuilds the published site automatically on every push to `main`.
