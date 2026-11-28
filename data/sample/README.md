# KFUPM corpus

The original PDFs: 34 public pages of King Fahd University of Petroleum & Minerals (KFUPM), saved as PDF:
the undergraduate regulations from the bulletin (`01-01` to `01-16`), registrar pages
(registration, calendars, exams, FAQs, transcripts) and registrar notices.

| File | What it is |
|---|---|
| `docs/` | The documents the agent searches. |
| `sources.csv` | One row per document: title, URL, date retrieved, licence, and what we changed. |
| `deadlines.csv` | The table behind the `get_deadline` tool (`name,date,note`, dates as `YYYY-MM-DD`). **The dates here are invented** for testing. |

Notes:

- The older 2011/2012 edition of the undergraduate regulations is left out on purpose: the `01-xx`
  files hold the current rules, and both together would put the same rule in the results twice.
- A few notices (`09`, `26`, `27`, `28`, `30`, `31`) have no source URL in the file.
- `31_Replacement_Certificate.pdf` is a scan: its extracted text is partly garbled.
- Two converted copies of these documents exist: `data/kfupm_structured/` (Markdown, one section per
  rule; the default) and `data/kfupm_raw/` (plain-text dump). See `CORPUS_DIR` in `config.py`.

## Swapping in another corpus

1. Make a new folder with the same layout, e.g. `data/campus/` containing `docs/`, `sources.csv` and `deadlines.csv`.
2. In `config.py`, set `CORPUS_DIR = ROOT / "data" / "campus"`.
3. Replace `eval/questions.json` with the matching evaluation questions.
4. Run `python scripts/smoke_test.py`.

Keep personal or private data out of `docs/`: free LLM tiers may log what you send them.
