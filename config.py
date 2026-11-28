# config.py
# Every setting for the workshop lives in this one file.
# Change a value, run your code again, and watch what happens.
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # the project folder (where this file is)

# ------------------------------------------------------------
# 1. Which LLM to use  (the ONE switch)
# ------------------------------------------------------------
# "groq", "gemini", "openrouter" or "local" (a small open model run by Ollama)
# Default: OpenRouter, using DeepSeek. See the "openrouter" entry below.
LLM_PROVIDER = "openrouter"

# All providers speak the same "OpenAI-compatible" API, so switching provider
# only changes the address (base_url), the model name and which key to use.
# "options" are extra settings sent with every request to that provider.
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b",              # or "openai/gpt-oss-120b" (smarter, slower)
        "key_name": "GROQ_API_KEY",
        "options": {"temperature": 0, "reasoning_effort": "low"},  # gpt-oss thinks first; "low" = think briefly
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.5-flash-lite",
        "key_name": "GEMINI_API_KEY",
        "options": {},                              # Gemini 3 ignores temperature, so we send none
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        # DeepSeek's stable chat model on OpenRouter. Other DeepSeek slugs:
        # "deepseek/deepseek-v4.1-flash" (cheaper, 1M context) or "deepseek/deepseek-v3.2".
        "model": "deepseek/deepseek-chat",
        "key_name": "OPENROUTER_API_KEY",
        "options": {"temperature": 0},
        # Optional OpenRouter headers (used for its dashboard/rankings).
        "headers": {
            "HTTP-Referer": "https://github.com/1Baleid/tuwaiq-agent-workshop",
            "X-Title": "Tuwaiq Agent Workshop",
        },
    },
    "local": {
        "base_url": "http://localhost:11434/v1",    # Ollama running on this machine / Colab VM
        "model": "qwen3:4b-instruct",
        "key_name": None,                           # no key needed
        "options": {"temperature": 0},
    },
}

LLM_TIMEOUT_SECONDS = 60     # give up on ONE LLM call after this many seconds
LLM_MAX_RETRIES = 3          # Session 2: how many times to retry a failed call (429, timeout, ...)
MAX_OUTPUT_TOKENS = 800      # longest reply we accept (models that "think" first need room)
# Note for students: choose the limit for the agent you are building:
#   - Q&A agent (agent.py): 800. Replies are short tool calls and answers.
#   - coding agent (harness_solution.py): 8000 (its MAX_REPLY_TOKENS). Replies carry code.

# ------------------------------------------------------------
# 2. Documents and search  (Session 3)
# ------------------------------------------------------------
# The same 34 KFUPM documents come in three copies. Pick one:
#   data/kfupm_raw         the default, used in the slides: one plain-text dump, no headings, lists or paragraphs
#   data/kfupm_structured  the same information as Markdown: one "## heading" section per complete rule
#                          (best with CHUNK_BY_SECTION = True)
#   data/sample            the original PDFs
# Every folder has the same layout: docs/ (the .txt, .md and .pdf files), sources.csv, deadlines.csv.
# Or set the CORPUS_DIR environment variable, e.g. CORPUS_DIR=data/kfupm_structured, without editing this file.
import os
CORPUS_DIR = ROOT / os.environ.get("CORPUS_DIR", "data/kfupm_raw")

# Small (90 MB) and fast, English only. It reads at most ~256 words per chunk.
# For Arabic documents use "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (470 MB).
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 120             # words per chunk (about one paragraph)
CHUNK_OVERLAP = 20           # words shared by two neighbouring chunks
CHUNK_BY_SECTION = False     # Session 3 fix: True = one chunk per section, labelled with its heading
TOP_K = 3                    # how many chunks one search returns
MIN_SCORE = 0.55             # Session 3: if no chunk scores this high, answer "I don't know"

# ------------------------------------------------------------
# 3. The agent  (Sessions 1-2)
# ------------------------------------------------------------
MAX_STEPS = 5                # most LLM calls the agent may make for ONE question
AGENT_TIMEOUT_SECONDS = 120  # most time the agent may spend on ONE question
MAX_HISTORY_TURNS = 3        # earlier questions + answers the agent remembers in a conversation
VERBOSE = True               # print every step the agent takes
LOG_FILE = ROOT / "logs" / "agent_log.jsonl"   # Session 2: one line per agent event

# ------------------------------------------------------------
# 4. Evaluation  (Session 5)
# ------------------------------------------------------------
EVAL_FILE = ROOT / "eval" / "questions.json"
