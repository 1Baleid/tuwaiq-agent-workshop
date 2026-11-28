# Build Your Own AI Harness: RAG that answers from your documents

Base code for the Tuwaiq Club workshop: 5 sessions, ~75% hands-on, Google Colab first.
Students build **one** project across the sessions: an agent that answers questions from a set of
documents, cites its sources, calls tools, and says "I don't know" when the documents don't say.

The project has two layers:

* **The RAG system** (`rag.py`, `answer.py`, `tools.py`, `llm.py`) is the target. It loads the
  documents, searches them, and turns the best passages into an answer with citations.
* **The harness** (`agent.py`) is what you build. A model can only reply with text; the harness
  turns that text into searches, tool calls and a final answer. Your system prompt and loop decide
  how well the model uses the RAG system.

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
| `rag.py` | 1 | load documents → chunks → embeddings → FAISS index → `search()` |
| `answer.py` | 2 | answer from the best chunks, with citations like `[course_credit.txt#3]`, or "I don't know" |
| `tools.py` | 3 | the tool registry: `search_docs`, `calculator`, `get_deadline`, plus `validate_call()` |
| `agent.py` | 3–4 | **you complete it:** the harness loop (7 short TODOs): prompt rules, JSON check, log, timeout, tool call |
| `llm.py` | all | `chat()` for every provider (one OpenAI-compatible client) and `chat_with_retries()` (S4) |
| `eval_runner.py` | 5 | runs `eval/questions.json` and shows a results table with failures flagged |
| `data/sample/` | | KFUPM corpus (34 public registrar and bulletin pages as PDF): `docs/`, `sources.csv`, `deadlines.csv` (see its README) |
| `notebooks/` | | `00_setup.ipynb` (pre-work) and `s5_evaluate.ipynb` (Session 5) |
| `scripts/` | | instructor tools (table below) |
| `docs/` | | decisions, pre-work, known errors, handovers |

## Build the harness (`agent.py`)

`agent.py` is the Session 3–4 file you complete. By then the rest of the repo gives you
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
* **Citations you can check.** Each chunk has an id like `course_credit.txt#3`. The prompt asks
  for that id after every fact; `answer.cited_sources()` keeps only ids that really exist.
* **A real "I don't know".** `MIN_SCORE` stops weak matches before the LLM sees them, and the
  prompt stops the LLM from filling the gap with a guess.
* **A small context.** `TOP_K`, `MAX_HISTORY_TURNS` and `MAX_OUTPUT_TOKENS` keep each call cheap
  and focused, so the model does not lose the question in a wall of text.
* **A trace.** `log_event()` records every question, retry, tool call and finish. When an answer
  is wrong, the log tells you whether retrieval, the prompt, or the model failed.

Compare your harness with `eval/questions.json`: a change is only an improvement if it makes more
of those questions pass without making the "I don't know" cases worse.

**Instructor reference:** `harness_solution.py` is a complete coding harness for a different
layer of the workshop: it lists, reads, writes and edits files, runs the workshop checks
(`smoke`, `eval`, `tests`), can ask the RAG system a question (`ask_rag`), refuses to write
`data/` or `eval/questions.json`, and will not accept an answer after an unverified edit.
`agent.py` is the RAG agent loop students build in Sessions 3–4. The solution file is
excluded from the student repo.

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

The instructor harness uses the same provider. To try another model for one run:
```bash
python harness_solution.py "your task" --model deepseek/deepseek-v4.1-flash
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

Copy the layout of `data/sample/` (`docs/`, `sources.csv`, `deadlines.csv`) into a new folder, set
`CORPUS_DIR` in `config.py`, replace `eval/questions.json`, and run `python scripts/smoke_test.py`.
For Arabic documents, also change `EMBEDDING_MODEL` (see the comment in `config.py`).

## Instructor tools

| Command | What it does |
|---|---|
| `python scripts/smoke_test.py [--quick]` | is everything working? (PASS / FAIL / TODO per step) |
| `python scripts/llm_probe.py groq gemini` | latency and tool-call check per provider |
| `python scripts/load_test.py shared --n 30` | can one key serve N students at once? (`burst` = one student) |
| `python scripts/tool_format_test.py local` | which tool-call format a model follows |
| `python scripts/local_model.py` | start the local fallback model |
| `python harness_solution.py "task"` | reference coding harness on OpenRouter + DeepSeek: inspect, edit and test the RAG code (instructor only; `--provider` / `--model` override) |
| `python scripts/make_main.py [--check]` | build `main` from `solutions` |
| `python scripts/publish_students.py [URL]` | copy both branches to the student repo (without internal docs) |
| `python eval_runner.py` | run the evaluation set from a terminal |
| `python tests/test_make_main.py` | tests for the branch generator |

## Versions

Pinned in `requirements.txt` (laptops): most versions match Google Colab's preinstalled packages
(November 2026, Python 3.13). pandas and scikit-learn use newer versions with Python 3.14 Windows
wheels. Dependency resolution has been checked for Python 3.13 and 3.14; Python 3.14 runtime
testing is still needed. `requirements-colab.txt` adds only what Colab lacks (`faiss-cpu`, `pypdf`).
FAISS was chosen over ChromaDB: on Colab it installs one package with no conflicts, while ChromaDB pulls
~84 packages, upgrades Colab's own packages, and needs the Visual C++ runtime on Windows.

## Docs

`docs/llm_options.md` (T1) · `docs/llm_decision.md` (T2) · `docs/prework.md` · `docs/known_errors.md` · `docs/handover/`

Documents: public pages of King Fahd University of Petroleum & Minerals (KFUPM), saved as PDF; source URL per file in `data/sample/sources.csv`.
