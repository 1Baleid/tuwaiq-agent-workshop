# Known errors: symptom → cause → fix → time limit

For floor helpers and instructors. Find the student's error message in the **Symptom** column.
**Time limit:** how long to try the fix before using the fallback. The general rule from the delivery plan
still applies: after **10 minutes** on one error, give the student the working file
(`!git checkout origin/solutions -- <file>`) and explain the error afterwards.

Entries marked **(seen)** happened while building and testing this repo (T1–T5). The others come from the
providers' official docs and the T1 research.

## 1. Installing (laptops)

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `Could not install packages due to an OSError: [Errno 2] No such file or directory … torch\include\…` and a hint about **Windows Long Path support** **(seen)** | Torch has very deep file paths; the project folder path is too long (common with OneDrive or "Documents\Courses\…") | Move the project to a short path such as `C:\work\tuwaiq`, delete `.venv`, create it again, reinstall | 10 min, then use Colab |
| `No matching distribution found for torch==2.11.0` on a Mac | Intel Macs have no PyTorch wheels any more | Use Colab | 2 min, then Colab |
| Installing on Linux downloads ~3 GB (`nvidia-…` packages) | PyPI's Linux torch includes CUDA | First run `pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu`, then the rest | 5 min, then Colab |
| `No matching distribution found for faiss-cpu==1.15.1` on an older Mac | faiss wheels need macOS 14+ (Apple Silicon) or 15+ (Intel) | Delete the `faiss-cpu==…` line from `requirements.txt` and run the install again. `rag.py` then uses plain numpy search (same results) | 5 min |
| pip cannot find the pinned versions, or the Python version is shown as 3.9 or older | Python too old | Install Python 3.13 from python.org, or use Colab | 10 min, then Colab |
| Very slow model or package downloads on the room Wi-Fi | 30 laptops sharing one connection | Use Colab (downloads happen on Google's network); laptop students should run the smoke test at home | 5 min, then Colab |

## 2. Keys and accounts

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `Colab could not read the secret GROQ_API_KEY (SecretNotFoundError)` | No secret with exactly that name | Secrets (key icon) → name exactly `GROQ_API_KEY` (or `GEMINI_API_KEY`) → run the cell again | 5 min |
| `Colab could not read the secret … (NotebookAccessError)` | "Notebook access" switch is off for this notebook | Turn **Notebook access** on next to the secret, run again | 2 min |
| `No GROQ_API_KEY found. Copy .env.example to .env …` (laptop) | No `.env` file, or the key line is empty | Copy `.env.example` to `.env` in the project folder, paste the key after `GROQ_API_KEY=` | 5 min |
| `AuthenticationError` / `401` / `Invalid API Key` (Groq), or `BadRequestError` / `400` with `Please pass a valid API key` or `Invalid Auth key` (Google) **(seen)** | Key copied wrongly (missing characters, spaces) or deleted | Create a new key, replace it in Secrets or `.env`, run the cell again. No restart needed: `llm.py` reads the key on every call | 5 min, then the local model |
| AI Studio says you must be **18 or older**, or asks for ID or card verification | Google's age rule | Do not try to get around it. The student uses the local model (`LLM_PROVIDER = "local"`) | stop at once |
| AI Studio: "access restricted by your admin" | A university / Workspace account | Use a personal Gmail account | 2 min |
| Gemini `401 … ACCESS_TOKEN_TYPE_UNSUPPORTED` | Reported in Oct 2026 with some new Google "auth keys" | Create a new key in a new project in AI Studio, or use Groq | 5 min |
| Gemini `403 PERMISSION_DENIED`, "Free tier unavailable" | This Google Cloud project is not allowed the free tier | Create a new project in AI Studio, or use Groq | 5 min |
| Creating a new Google account asks for a phone number | Google's anti-abuse check | Use your own phone number, at home, before the workshop | n/a |

## 3. Rate limits and provider errors

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `RateLimitError` / `429` from Groq, or the agent log shows `[retry] … RateLimitError` | Groq free tier: 8,000 tokens per minute per student. A fast run of questions goes over it | Nothing: the agent waits and retries by itself (Session 4). If it keeps happening, wait a minute between questions | 2 min, then switch provider |
| Gemini `429` that does not go away after a minute | Daily quota used up. It resets at midnight Pacific time, which is 11:00 in Riyadh | Switch provider (`config.LLM_PROVIDER = "groq"` or `"local"`). Failed calls count against the quota too | at once |
| `503` / "overloaded" from Gemini | Google's servers are busy | Retry after a minute or switch provider | 2 min |
| Every student gets 429s at the same moment | Students are sharing one key | Every student must use their own key (see `docs/llm_decision.md`) | at once |
| `NotFoundError` / `404` / `400` mentioning the model ("not found", "decommissioned", "no longer available") | The provider retired the model (Groq retired its free Llama models on 2026-08-16) | Put a current model name in `config.py` → `PROVIDERS` (see `docs/llm_options.md`); check with `python scripts/llm_probe.py` | 5 min |

## 4. Colab

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| "Unable to connect to the runtime" / "Failed to fetch" | Network or DNS problem. In Oct 2026 some ISPs could not resolve `*.prod.r.colab.dev` | Try a phone hotspot, turn off VPN. Ask the venue IT to allow `*.prod.r.colab.dev` before the workshop | 5 min |
| "Warning: This notebook was not authored by Google" with **Cancel** / **Run anyway** | Normal for notebooks opened from GitHub | Click **Run anyway** | 1 min |
| Colab asks to **grant this notebook access** to a secret | "Notebook access" was off for that secret | Click **Grant access** | 1 min |
| `NameError: name 'config' is not defined` (or `rag`, `llm` …) | The session restarted or disconnected and Python forgot everything | Run the first cell again, then the cells above the one that failed | 2 min |
| Edited `rag.py` (or another `.py` file) but nothing changed | Python keeps the old version loaded | **Runtime → Restart session**, then run from the top | 2 min |
| "Cannot connect to GPU backend" / no GPU offered | Free Colab GPUs are limited and not guaranteed | Use a CPU runtime with Groq or Gemini. Only the local model needs a GPU | at once |
| A red pip "dependency conflicts" message after installing something extra | The extra package changed Colab's own packages. Our setup installs only `faiss-cpu` and `pypdf` | Only install what the notebook installs. If it is already done: **Runtime → Restart session** | 5 min |

## 5. Models and downloads

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN …` **(seen)** | Downloading the embedding model without a Hugging Face account | Harmless: no Hugging Face key is needed. `rag.embed` now hides it; it can still appear if other code downloads from Hugging Face | n/a |
| `To support symlinks on Windows, you either need to activate Developer Mode …` **(seen)** | Hugging Face cache on Windows | Harmless: ignore it (it just uses more disk) | n/a |
| `NOTE: Redirects are currently not supported in Windows or MacOs.` **(seen)** | A torch message on Windows/macOS | Harmless: ignore it | n/a |
| Ollama install in Colab stops with `This version requires zstd for extraction` **(found in T1)** | The Colab VM has no `zstd` | Use `scripts/local_model.py`: it installs `zstd` first | 5 min |
| Installer says "The Ollama API is now available", but connecting to `localhost:11434` fails **(found in T1)** | Colab has no systemd, so nothing started the server | Use `scripts/local_model.py`: it starts `ollama serve` itself | 5 min |
| Local model takes 20–40 s per answer **(seen, CPU test)** | No GPU | **Runtime → Change runtime type → T4 GPU**, run cell 1 and the Plan B cell again | 5 min |
| Local model forgets the instructions or the tool list in long conversations | Ollama's default context is 4,096 tokens and it cuts longer prompts **silently** | Start the server with `OLLAMA_CONTEXT_LENGTH=8192`. `scripts/local_model.py` does this, but only when it starts the server itself, so restart Ollama (on a laptop) or the Colab session | 5 min |
| The first local answer after a pause is slow | Ollama unloads the model after 5 idle minutes | `scripts/local_model.py` starts the server with `OLLAMA_KEEP_ALIVE=-1` (keep loaded) | n/a |

## 6. The agent and its tools (Sessions 3–4)

| Symptom (in the agent's log) | Cause | Fix | Time limit |
|---|---|---|---|
| `[bad_json] … your reply has no JSON object` **(seen)** | The model answered in plain text, e.g. just "I don't know based on the documents." | Normally nothing: the harness tells the model and it fixes it next step. If it repeats, check the examples in `SYSTEM_PROMPT` are still there, or use a stronger model | 10 min |
| `[bad_tool_call] Unknown tool '…'` or `… is missing: …` | The model invented a tool or forgot an argument | Normally nothing: `validate_call` sends the error back and the model retries. On `main` this is the Session 3 exercise | 10 min |
| Answer `Sorry, I could not finish … (stopped: max_steps)` | The agent kept calling tools, e.g. the same tool again and again | Read the log: what did the tool answer? Usually a tool error the model cannot fix. Raise `MAX_STEPS` only if the question really needs more steps | 10 min |
| `(stopped: timeout)` | A slow provider, or long waits after 429s | Raise `AGENT_TIMEOUT_SECONDS`, or switch provider | 5 min |
| `(stopped: llm_error)` | The LLM could not be reached even after retries: network, key or provider down | Check the error in the log; switch provider | 5 min |
| The answer is right but cites nothing, or the model answered without searching **(seen with the small local model)** | Small models sometimes answer from memory | Expected sometimes. A good discussion point for S3 ("raw model vs harness"). A stronger model (Groq) does it less | n/a |
| `"I don't know"` for a question that **is** in the documents | The file was not loaded (look for `Skipped … file(s)` when the index is built), `MIN_SCORE` is too high, or the chunks are too small or too big | Check the loader's output and `rag.search(rag.get_store(), "your question")` scores. Lower `MIN_SCORE` a little. Rebuild | 10 min |
| Calculator error `'(2, 400 * 1.15)' is not allowed …` | The model wrote a number with a thousands comma, `2,400` | Normally the model retries without the comma. Otherwise rephrase without commas | 5 min |
| `Warning: chunk/model/corpus settings changed since build_store(). Run build_store() again.` | A store built before `CHUNK_SIZE` (etc.) was changed | Build it again: `store = rag.build_store()` (`rag.get_store()` rebuilds by itself) | 2 min |

## 7. Data and documents

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `Skipped 1 file(s) this loader cannot read: …` | The loader reads only `.txt`, `.md` and `.pdf` | Convert the file to `.txt` or `.pdf` (or extend `rag.read_file`, as in Session 5) | 10 min |
| `get_deadline` says `The date of '…' in deadlines.csv is not a valid YYYY-MM-DD date.` | A date typed like `17/12/2026`, often by Excel | Write dates as `2026-12-17` in `deadlines.csv` (or extend `tools.parse_date`, as in Session 5) | 5 min |
| `get_deadline` says `No deadline called '…'` | The name in the question is not exactly the name in `deadlines.csv` | Use the exact name, or make `tools.find_deadline` match similar names (Session 5) | 5 min |
| `UnicodeDecodeError: 'utf-8' codec can't decode …` when loading documents | The file was saved in another encoding (e.g. Arabic Windows-1256) | Open it and save it again as **UTF-8** | 5 min |
| `UnicodeEncodeError: 'charmap' codec can't encode …` when printing on Windows **(seen)** | The Windows console uses an old code page (cp1256 on Arabic Windows) | Run with `python -X utf8 …`, or set the environment variable `PYTHONUTF8=1` | 2 min |
| Tables or footnote marks like `[4]` from PDFs appear in answers | PDF text keeps the document's footnote marks | Harmless. Our citations look like `[file.txt#3]`, so they cannot be confused | n/a |

## 8. For maintainers (the repo itself)

| Symptom | Cause | Fix | Time limit |
|---|---|---|---|
| `make_main.py --check` says `differs: data/sample/sources.csv` **(seen)** | Windows line endings (CRLF) on disk, e.g. from Python's csv writer; git stores LF | Fixed: `make_main.py` reads files from the commit. Run `git checkout -- <file>` to tidy the working copy | n/a |
| `make_main.py`: `SOLUTION START without SOLUTION END` (or the reverse) | Unbalanced markers in a `.py` file or notebook cell | Fix the markers; `python tests/test_make_main.py` checks every file | 5 min |
| A student's `git checkout origin/solutions -- rag.py` fails with "pathspec … did not match" | Run outside the project folder, or the clone has no `origin/solutions` | In Colab, run cell 1 first (it goes into the project folder). Check with `!git branch -a` | 5 min |
