# Build Your Own AI Harness: RAG that answers from your documents

Base code for the Tuwaiq Club workshop: 5 sessions, ~75% hands-on, Google Colab first.
Students build **one** project across the sessions: an agent that answers questions from a set of
documents, cites its sources, calls tools, and says "I don't know" when the documents don't say.

The project has two layers:

* **The RAG system** (`rag.py`, `answer.py`, `tools.py`, `llm.py`) is the target. It loads the
  documents, searches them, and turns the best passages into an answer with citations.
* **The Q&A agent** (`agent.py`, Sessions 1-2) is the loop you complete: a model can only reply with
  text, and the loop turns that text into searches, tool calls and a final answer.
* **The coding harness** (`harness.py`, Session 3) is given complete. You ask it, in plain English, to
  build the empty functions of the RAG system, and you check what it wrote.

By the end you have a personalized harness tuned for RAG: it retrieves before it answers, cites
the chunks it used, refuses to guess, and logs every step so you can see why it failed.

Plain Python, no LangChain or LlamaIndex, so every mechanism is visible.

## Quick start

**In Colab (students):** open `notebooks/00_setup.ipynb` in Colab and run the cells top to bottom.
It downloads this repo, checks your API key (from Colab Secrets) and runs the smoke test.

**On a laptop** (Python 3.14; Colab uses Python 3.13):

```bash
git clone https://github.com/1Baleid/tuwaiq-agent-workshop.git tuwaiq && cd tuwaiq
python -m venv .venv
.venv\Scripts\activate                 # Windows   (macOS/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt
copy .env.example .env                 # macOS/Linux: cp .env.example .env   then set OPENROUTER_API_KEY
python scripts/smoke_test.py
```

## What is where

| File | Session | What it does |
|---|---|---|
| `config.py` | all | **Every setting**, including the one LLM switch `LLM_PROVIDER` |
| `rag.py` | 3 | **built with the harness:** load documents → chunks → embeddings → ChromaDB index → `search_docs()` (empty functions + specification) |
| `answer.py` | 3 | **built with the harness:** answer from the best chunks, with citations like `[1]`, or "I don't know" |
| `harness.py` | 3 | **given complete:** the coding harness you ask to build `rag.py` and `answer.py` (see below) |
| `tools.py` | 1–2 | the tool registry: `search_docs`, `calculator`, `get_deadline`, plus `validate_call()` |
| `agent.py` | 1–2 | **you complete it:** the Q&A agent loop (7 short TODOs): prompt rules, JSON check, log, timeout, tool call |
| `llm.py` | all | `chat()` for every provider (one OpenAI-compatible client) and `chat_with_retries()` (given complete: the harness needs it) |
| `eval_runner.py` | 5 | runs `eval/questions.json` and shows a results table with failures flagged |
| `data/` | | the 34 KFUPM documents in three folders: `kfupm_raw/` (plain text, default, used in the slides), `kfupm_structured/` (Markdown), `kfupm_pdf/` (originals), plus `deadlines.csv`. See `data/README.md` |
| `notebooks/` | | `00_setup.ipynb` (pre-work) and `s5_evaluate.ipynb` (Session 5) |
| `scripts/` | | instructor tools (table below) |
| `docs/` | | decisions, pre-work, known errors, handovers |

## Use the coding harness (`harness.py`, Session 3)

In Session 3 you do not type the RAG code yourself: you ask the coding harness to build it, the way
you would ask Claude Code or Codex. The functions in `rag.py` and `answer.py` are **empty**; each has a
docstring (what it returns) and numbered comments (how). Together they are the specification the
harness follows. Your job is to give it good requests, watch it work, and check what it built.

**How to ask it something:** run the file with your request in quotes, from the project folder.

```bash
cd tuwaiq                                   # the project folder (cd goes into folders, not files)
python harness.py "Which functions in rag.py are still empty? Do not change anything."
```

In Colab, put `!` in front: `!python harness.py "..."`.

It prints every step while it works (`read_file`, `edit_file`, `run_check`, ...) and ends with its
answer. **One request per run:** each run starts fresh and does not remember the previous one.

**One step per request works best.** A good order for Session 3:

```bash
python harness.py "Write read_file and load_documents in rag.py, then run run_check('load')"
python harness.py "Write chunk_text and make_chunks in rag.py, then run run_check('chunks')"
python harness.py "Write embed, numpy_search, build_index and search_docs in rag.py, then run run_check('search')"
python harness.py "Write split_sections and chunk_by_section in rag.py, then run run_check('sections')"
python harness.py "Write the four empty functions in answer.py, then run run_check('answer')"
```

**After every request, check its work:**

* `git diff rag.py` shows exactly what it changed. Read it: can you explain each line?
* `python scripts/smoke_test.py` runs every check yourself (PASS / FAIL / TODO).
* `logs/harness.jsonl` has every step it took, when you need to know why it got stuck.
* `git restore rag.py` throws its changes away, so you can try again with a better request.

**Its checks:** one per step: `load`, `chunks` (incl. the id format), `search`, `sections`, and
`answer` for `answer.py`; `rag` runs all four `rag.py` checks. Name the check in your request. The harness may not finish until the check it ran
after its last edit passes. What the checks do not test, it can still get wrong: that is why you read
the diff.

**Safety:** its file tools stay inside the project, refuse to open `.env` (your key), and cannot change
`data/` or `eval/questions.json`; it runs only `python`, `pytest` and read-only `git`. These are guard
rails for class, not a sandbox (`python` can still do anything you can), so run it on your own copy of
the project and read its changes before you keep them.

## The Q&A agent (`agent.py`, Sessions 1–2)

`agent.py` is the Session 1–2 file you complete. The rest of the repo gives you
the pieces: `rag.py` finds chunks, `answer.py` formats and checks citations, `tools.py` runs the
tool calls, and `llm.py` talks to the model. `chat_server.py`, `eval_runner.py` and
`scripts/smoke_test.py` all call `agent.run_agent()`, so keep its return contract (documented in
the file).

The scaffold already has the loop, the JSON parsing, the error handling and the result contract.
You fill in seven small TODOs:

1. **Prompt rules (TODOs 1–3):** tell the model to search first, cite sources, and say
   "I don't know".
2. **`parse_reply()` (TODO 4):** reject a JSON object that has neither `answer` nor `tool`.
3. **`log_event()` (TODO 5):** append one JSON line to `config.LOG_FILE`.
4. **`run_agent()` (TODOs 6–7):** add the timeout check, then validate and run the tool call
   and send the result back.

A harness that is good at RAG does five things:

* **Retrieval before generation.** The prompt tells the model to call `search_docs` first, and the
  loop sends the retrieved chunks back as a tool result. The model never answers from memory.
* **Citations you can check.** Each chunk has an id like `01-05_Attendance_And_Withdrawal.md#3`. The prompt asks
  for that id after every fact; `answer.cited_sources()` keeps only ids that really exist.
* **A real "I don't know".** `MIN_SCORE` stops weak matches before the LLM sees them, and the
  prompt stops the LLM from filling the gap with a guess.
* **A small context.** `TOP_K`, `MAX_HISTORY_TURNS` and `MAX_OUTPUT_TOKENS` keep each call cheap
  and focused, so the model does not lose the question in a wall of text.
* **A trace.** `log_event()` records every question, retry, tool call and finish. When an answer
  is wrong, the log tells you whether retrieval, the prompt, or the model failed.

Compare your harness with `eval/questions.json`: a change is only an improvement if it makes more
of those questions pass without making the "I don't know" cases worse.

## Settings to change on purpose ("break it, then fix it")

All in `config.py`, as plain variables. Functions read them **when they run**, so in a notebook
`config.TOP_K = 1` takes effect immediately; changing `CHUNK_SIZE` rebuilds the index automatically.

| Setting | Default | Try |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 120 / 20 words | 15 or 1000: search results get worse |
| `CHUNK_BY_SECTION` | `False` | `True`: one chunk per section, labelled with its heading (the fix) |
| `TOP_K` | 3 chunks per search | 1: answers miss facts |
| `MIN_SCORE` | 0.55 | 0.0: off-topic questions now come with "sources", so only the LLM stands between you and a made-up answer |
| `MAX_STEPS` | 5 LLM calls per question | 1: tool questions stop before answering |
| `AGENT_TIMEOUT_SECONDS` / `LLM_TIMEOUT_SECONDS` | 120 / 60 | 1: watch timeouts and retries |
| `LLM_PROVIDER` | `"openrouter"` | `"local"`: the fallback model (see below) |

## Switching the LLM

`LLM_PROVIDER` in `config.py` picks one entry of `PROVIDERS`: `openrouter` (default), `groq`,
`gemini`, or `local`. Every provider uses the same OpenAI-compatible client, so nothing else changes.
Keys come from Colab Secrets or `.env` (`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`);
see `docs/llm_options.md`.

### OpenRouter + DeepSeek (default)

1. Create a key at **https://openrouter.ai/keys**.
2. Put it in `.env` (laptop) or Colab Secrets:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
3. Check the connection:
   ```bash
   python scripts/smoke_test.py --quick
   ```
   The LLM line should say `openrouter / deepseek/deepseek-chat replied 'OK' ...`.

The `openrouter` entry in `config.py` uses `deepseek/deepseek-chat`. Swap that line for
`deepseek/deepseek-v4.1-flash` (cheaper, 1M context) or `deepseek/deepseek-v3.2` if you prefer.
OpenRouter is OpenAI-compatible, so `llm.py` does not change.

The coding harness uses the same provider. To try another model for one run:
```bash
python harness.py "your task" --model deepseek/deepseek-v4.1-flash
```

**Plan B, `local`:** a small open model (`qwen3:4b-instruct`) run by Ollama inside each student's
own Colab. It needs a GPU runtime. `scripts/local_model.py` installs and starts it (cell "Plan B" in `00_setup.ipynb`).

**Tool-call format:** the agent asks the model to reply with plain JSON (`{"tool": ..., "args": ...}` or
`{"answer": ...}`), not the provider's native tool-calling. That works with every provider and the local
model, and students see the parsing and validation happen. The test is in `docs/llm_options.md`.

## Branches: `main` (with TODOs) and `solutions`

* **Only ever edit `solutions`.** Code that students write in a session is wrapped in markers:

  ```python
  # SOLUTION START: TODO (Session 3): cut `text` into chunks of `size` characters
  ...working code...
  # SOLUTION END
  ```

  On `main` the block becomes that TODO comment plus `raise NotImplementedError(...)`. Add a
  `# SOLUTION ELSE` part (commented-out lines) when `main` must still run, e.g. "no retries yet".
  Markers work in `.py` files and in notebook code cells.
* **Regenerate `main`** after committing on `solutions`: `python scripts/make_main.py`.
  `python scripts/make_main.py --check` fails if `main` has drifted. `--show rag.py` previews one file.
* **Two repos:** the team repo (this one, with internal docs) and the student repo that participants clone.
  `python scripts/publish_students.py` copies both branches to the student repo, minus the internal docs.
  See `HANDOVER.md` (team repo only).
* **Stuck student (10-minute rule):** get the working version of one file:
  `git checkout origin/solutions -- rag.py` (in Colab: prefix with `!`).
* On `main`, the smoke test shows unfinished exercises as **TODO**, not FAIL.

## Swapping the corpus

Put the new documents (`.txt`, `.md` or `.pdf`) in a new folder such as `data/campus/`, set `CORPUS_DIR`
in `config.py`, update `data/deadlines.csv` and `eval/questions.json`, and run `python scripts/smoke_test.py`.
For Arabic documents, also change `EMBEDDING_MODEL` (see the comment in `config.py`).

## Instructor tools

| Command | What it does |
|---|---|
| `python scripts/smoke_test.py [--quick]` | is everything working? (PASS / FAIL / TODO per step) |
| `python scripts/llm_probe.py groq gemini` | latency and tool-call check per provider |
| `python scripts/load_test.py shared --n 30` | can one key serve N students at once? (`burst` = one student) |
| `python scripts/tool_format_test.py local` | which tool-call format a model follows |
| `python scripts/local_model.py` | start the local fallback model |
| `python harness.py "task"` | the coding harness: inspect, edit and test the RAG code (`--provider` / `--model` override, `--print-prompt` shows its prompt) |
| `python scripts/make_main.py [--check]` | build `main` from `solutions` |
| `python scripts/publish_students.py [URL]` | copy both branches to the student repo (without internal docs) |
| `python eval_runner.py` | run the evaluation set from a terminal |
| `python tests/test_make_main.py` | tests for the branch generator |

## Versions

Pinned in `requirements.txt` (laptops): most versions match Google Colab's preinstalled packages
(November 2026, Python 3.13). pandas and scikit-learn use newer versions with Python 3.14 Windows
wheels. Dependency resolution has been checked for Python 3.13 and 3.14; Python 3.14 runtime
testing is still needed. `requirements-colab.txt` adds only what Colab lacks (`chromadb`, `pypdf`).
Without `chromadb`, `rag.py` falls back to plain numpy search (same results).

## Docs

`docs/llm_options.md` (T1) · `docs/llm_decision.md` (T2) · `docs/prework.md` · `docs/known_errors.md` · `docs/handover/`

Documents: public pages of King Fahd University of Petroleum & Minerals (KFUPM); the source of every file is listed in `data/README.md`.
