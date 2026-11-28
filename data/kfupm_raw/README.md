# KFUPM corpus: raw copy

The same information as `data/kfupm_structured/`, dumped as plain text: no headings, no lists and no
paragraphs, just the words of each document in order. Use it to see what chunking does when a
document has no structure to follow (`CHUNK_BY_SECTION` has no headings to split on here).

Switch to it with `CORPUS_DIR = ROOT / "data/kfupm_raw"` in `config.py`, or the environment variable
`CORPUS_DIR=data/kfupm_raw`. Source URLs are in `sources.csv`.
