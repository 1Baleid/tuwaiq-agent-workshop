# LLM access decision (ticket T2)

Written 2026-11-02. **Status:** a recommendation. The final provider choice needs the technical lead's OK. The real-provider load tests are **waiting for API keys**; the commands to finish them are at the end.

## Recommendation

1. **Give every student their own free key: Groq as the main provider, Gemini as a second key.**
   - Free limits are counted per account. A shared free key gives the whole class *one* student's budget, which is far too small (see the table below).
   - Groq's and Google's terms also forbid sharing keys or pooling many free accounts to get around limits.
   - The second (Gemini) key is what lets the "one setting" switch work on the day if Groq has an outage.
2. **The local model is the fallback, for outages and for under-18 students.** Each student runs Ollama + `qwen3:4b-instruct` in their **own** Colab GPU runtime. The "proven" section below shows it working through the single setting.
3. **Optional, needs budget approval: one shared *paid* Groq key.** Groq's paid tier allows 250K tokens/min and 1K requests/min per model. At list prices our whole workshop would cost about **$2–10** on `gpt-oss-20b`. Groq also says it offers event credits ("promotional credits, such as during hackathons and special events"), which could make it free. This option also helps under-18 students:
   - Groq's terms let an organization's application serve under-18 end users, with the organization responsible.
   - **Confirm this with Groq** when asking for credits.
   - I have **not** done anything that costs money.

## Why not a shared free key? (official limits, per account)

| Plan | Capacity for the whole class | Cost | Verdict |
|---|---|---|---|
| **Free key per student (Groq)** | Each student: 30 req/min, **8K tokens/min**, 200K tokens/day | Free | **Recommended** |
| One shared free Groq key | Whole class: 8K tokens/min ≈ **7 LLM calls per minute** in total. 30 students asking one question each need about 90 | Free, but against Groq's terms | No |
| One shared free Gemini key | Whole class: ~10 req/min, ~500 req/day (unofficial figures) | Free, but against Google's terms | No |
| One shared **paid** Groq key | 250K tokens/min ≈ 240 calls/min. Normal use is about 90 calls/min, and an S5 evaluation burst about 180 | ≈ $2–10 for the workshop | Option, if approved |
| Local model, one per student | One user per Colab VM, so there is no shared limit | Free | Fallback; needs a GPU runtime |

One agent question in our tests = 3–4 calls of about 1,050 tokens each. So one question ≈ **4,200 tokens**, against Groq's 8,000 tokens/min per account.

## Load test (`scripts/load_test.py`)

Each call uses a realistic agent prompt: the instructions, ~1,000 tokens of document chunks, and the steps so far. `max_retries=0`, so every 429 is **counted, not hidden**. A run **passes** when ≥ 95% of calls succeed **and** p95 latency ≤ 15 s.

| Scenario | Provider | Calls | Success | 429s | p50 | p95 | Result |
|---|---|---|---|---|---|---|---|
| **(b) one student's burst:** 3 questions × 4 calls | **local** (`qwen3:4b-instruct`, GTX 1060), chosen **only by setting `LLM_PROVIDER = "local"`** | 12 | **100%** | 0 | 0.7 s | 4.2 s | **PASS** |
| (a) 30 calls at once on **one** local server | local | 30 | 90% (3 timeouts at 120 s) | 0 | 57 s | 107 s | **FAIL**, as expected |
| (a) shared key, N = 30 | Groq | 30 | *pending key* | | | | |
| (b) one student's burst | Groq | 12 | *pending key* | | | | |
| (a) shared key, N = 30 | Gemini | 30 | *pending key* | | | | |
| (b) one student's burst | Gemini | 12 | *pending key* | | | | |

What the local runs tell us:
- **The fallback works through the single setting.** I changed only `LLM_PROVIDER` from `"groq"` to `"local"` in `config.py` and ran `python scripts/load_test.py burst` with no other flag: 12 of 12 calls OK, PASS. Then I set it back.
- **One shared local server cannot serve the class.** Ollama answers one request at a time, so 30 simultaneous calls queued for up to 2 minutes. Colab's rules also forbid serving others from a notebook. **Every student runs their own model.**
- **Prompt caching matters.** In the burst, **72% of prompt tokens were served from the cache**, because an agent's steps share the same start. Groq says cached tokens don't count against its limits (on `gpt-oss` models). If that holds, one student's burst stays far below 8K tokens/min; without caching it would not. **The Groq burst run will settle this.**

## How to finish T2 (≈ 15 minutes, once keys are in `.env`)

```
python scripts/load_test.py shared --n 30                      # (a) Groq, one key, 30 at once
python scripts/load_test.py burst                              # (b) Groq, one student's burst
python scripts/load_test.py shared --n 30 --provider gemini
python scripts/load_test.py burst --provider gemini
```

Each run prints the numbers for the table and saves a JSON file in `results/`. Expected results:
- **(a) fails on both providers** (many 429s). That *is* the evidence against a shared free key.
- **(b) should pass** on Groq. If (b) fails on Groq, the fallback plan is Gemini keys, or the paid/credits option above.

N defaults to 30. Change it with `--n` once attendance is confirmed.
