# Building Intelligent AI Agents: RAG & AI Harness (starter repo)

Base code for the Tuwaiq Club workshop: 5 sessions, ~75% hands-on, Google Colab first.
Students build **one** project across the sessions: an agent that answers questions from a set of
documents, cites its sources, calls tools, and says "I don't know" when the documents don't say.

Plain Python, no LangChain or LlamaIndex, so every mechanism is visible.

## Quick start

**In Colab (students):** open `notebooks/00_setup.ipynb` in Colab and run the cells top to bottom.
It downloads this repo, checks your API key (from Colab Secrets) and runs the smoke test.

**On a laptop** (Python 3.13 recommended; it is what Colab uses):

```bash
git clone https://github.com/1Baleid/tuwaiq-agent-workshop.git tuwaiq && cd tuwaiq
python -m venv .venv
.venv\Scripts\activate                 # Windows   (macOS/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt
copy .env.example .env                 # macOS/Linux: cp .env.example .env   then paste your key into .env
python scripts/smoke_test.py
```

## What is where

| File | Session | What it does |
|---|---|---|
| `config.py` | all | **Every setting**, including the one LLM switch `LLM_PROVIDER` |
| `rag.py` | 1 | load documents → chunks → embeddings → FAISS index → `search()` |
| `answer.py` | 2 | answer from the best chunks, with citations like `[course_credit.txt#3]`, or "I don't know" |
| `tools.py` | 3 | the tool registry: `search_docs`, `calculator`, `get_deadline`, plus `validate_call()` |
| `agent.py` | 3–4 | the agent loop: tool calls as plain JSON, validation, step limit, timeout, retries, log file |
| `llm.py` | all | `chat()` for every provider (one OpenAI-compatible client) and `chat_with_retries()` (S4) |
| `eval_runner.py` | 5 | runs `eval/questions.json` and shows a results table with failures flagged |
| `data/sample/` | | placeholder corpus: `docs/`, `sources.csv`, `deadlines.csv` (see its README) |
| `notebooks/` | | `00_setup.ipynb` (pre-work) and `s5_evaluate.ipynb` (Session 5) |
| `scripts/` | | instructor tools (table below) |
| `docs/` | | decisions, pre-work, known errors, handovers |

## Settings to change on purpose ("break it, then fix it")

All in `config.py`, as plain variables. Functions read them **when they run**, so in a notebook
`config.TOP_K = 1` takes effect immediately; changing `CHUNK_SIZE` rebuilds the index automatically.

| Setting | Default | Try |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 500 / 100 characters | 50 or 3000: search results get worse |
| `TOP_K` | 4 chunks per search | 1: answers miss facts |
| `MIN_SCORE` | 0.40 | 0.0: off-topic questions now come with "sources", so only the LLM stands between you and a made-up answer |
| `MAX_STEPS` | 5 LLM calls per question | 1: tool questions stop before answering |
| `AGENT_TIMEOUT_SECONDS` / `LLM_TIMEOUT_SECONDS` | 120 / 60 | 1: watch timeouts and retries |
| `LLM_PROVIDER` | `"groq"` | `"local"`: the fallback model (see below) |

## Switching the LLM

`LLM_PROVIDER` in `config.py` picks one entry of `PROVIDERS`: `groq` (default), `gemini`, `openrouter`, or `local`.
Every provider uses the same OpenAI-compatible client, so nothing else changes. Keys come from Colab
Secrets or `.env` (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`); see `docs/llm_options.md`.

**Plan B, `local`:** a small open model (`qwen3:4b-instruct`) run by Ollama inside each student's
own Colab. It needs a GPU runtime. `scripts/local_model.py` installs and starts it (cell "Plan B" in `00_setup.ipynb`).

**Tool-call format:** the agent asks the model to reply with plain JSON (`{"tool": ..., "args": ...}` or
`{"answer": ...}`), not the provider's native tool-calling. That works with every provider and the local
model, and students see the parsing and validation happen. The test is in `docs/llm_options.md`.

## Branches: `main` (with TODOs) and `solutions`

* **Only ever edit `solutions`.** Code that students write in a session is wrapped in markers:

  ```python
  # SOLUTION START: TODO (Session 1): cut `text` into chunks of `size` characters
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
| `python scripts/make_main.py [--check]` | build `main` from `solutions` |
| `python scripts/publish_students.py [URL]` | copy both branches to the student repo (without internal docs) |
| `python eval_runner.py` | run the evaluation set from a terminal |
| `python tests/test_make_main.py` | tests for the branch generator |

## Versions

Pinned in `requirements.txt` (laptops): every version equals Google Colab's preinstalled version
(November 2026, Python 3.13). `requirements-colab.txt` adds only what Colab lacks (`faiss-cpu`, `pypdf`).
FAISS was chosen over ChromaDB: on Colab it installs one package with no conflicts, while ChromaDB pulls
~84 packages, upgrades Colab's own packages, and needs the Visual C++ runtime on Windows.

## Docs

`docs/llm_options.md` (T1) · `docs/llm_decision.md` (T2) · `docs/prework.md` · `docs/known_errors.md` · `docs/handover/`

Sample documents: Wikipedia, CC BY-SA 4.0 (see `data/sample/sources.csv`).
