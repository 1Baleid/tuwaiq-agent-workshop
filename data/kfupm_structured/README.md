# KFUPM corpus: structured copy

The 34 KFUPM documents from `data/sample/` rewritten as Markdown, built for section chunking:

- Every `## heading` section holds one complete rule, so a chunk never starts in the middle of one.
- Each heading says what the rule is about (for example "Unexcused absences over 20% give a DN grade"),
  and `chunk_by_section()` puts the file title and heading in front of every chunk.
- The wording of the rules is kept. Tables (grades, calendars, timetables) are turned into lists,
  rules the Registrar has since changed are marked `[UPDATED RULE]`, and places where the source page
  leaves a list out say so in square brackets.
- 253 sections: 240 fit in 120 words, the longest has 167 (set `CHUNK_SIZE = 170` to keep all whole).

Use it with `CHUNK_BY_SECTION = True` in `config.py`. Compare with `data/kfupm_raw/`, the same
information with no structure. Source URLs are in `sources.csv`.
