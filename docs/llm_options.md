# LLM options: free tiers compared (ticket T1)

Checked on **2026-11-02**, from a home connection in Saudi Arabia. Limits and terms come from each provider's official docs (links at the end). Measurements were taken on this laptop: Windows 10, GTX 1060 6 GB.
**Status:** comparison only. Choosing the provider is ticket T2 and needs the technical lead's approval.

## The short version

1. **Every hosted free tier is 18+ only.** The terms of Groq, Google (Gemini) and OpenRouter all require users to be 18 or older. Students under 18 can only use the local model in Colab. **Add an age question to the sign-up form.**
2. **Groq is the strongest primary option.** Use `openai/gpt-oss-20b`. Its free models are production models, it is fast (about 2 s per agent question in independent benchmarks), it is OpenAI-compatible, and Saudi customers contract with Groq Limited (Riyadh). The catch is **8,000 tokens per minute per account**, which is about 1–2 agent questions per minute for each student.
3. **Gemini is the backup.** Use `gemini-3.5-flash-lite`. Google no longer publishes free limits; the unofficial figures are about 10–15 requests/min and 500/day per student, and failed requests count too. It always "thinks", which makes it about 10× slower: around 20 s per agent question. Free-tier prompts may be used for training, and new projects sometimes get 429/503 errors on their first call.
4. **OpenRouter's free tier is not usable for the class.** It allows 50 requests per day per account, and a single S5 evaluation run uses about 30. Gemma 4 is the only well-known free model family, and its Terms say credits must be bought.
5. **The local fallback works, but only on a GPU.** Ollama with `qwen3:4b-instruct` passed 10/10 tool-call tests and took about 5 s per call here (Colab's T4 is faster than this GPU). Without a GPU, a call takes 20–40 s. Free Colab does **not** guarantee a GPU.
6. **One shared free key cannot serve 30 students.** The whole class would share one account's limits: 8K tokens/min on Groq, 10 requests/min on Gemini. Groq's and Google's terms also forbid pooling accounts or sharing keys. Ticket T2 measures this.
7. **Worth asking (input to T2): Groq says it "occasionally offer[s] promotional credits, such as during hackathons and special events".** Event credits would unlock its paid tier (250K tokens/min) for one shared class key. At list price, the whole workshop would cost about $2–10 on `gpt-oss-20b`.

## What our workshop asks of an LLM

- One agent question = **2–5 calls** of about **1,000–2,500 tokens** each: instructions, retrieved chunks, tool results.
- Up to **30 students** calling at the same moment, for two hours a day.
- So the limits that matter are **tokens per minute (TPM)** and **requests per day (RPD), per student**, more than raw speed.

## Comparison

| | **Groq** | **Google Gemini API** | **OpenRouter (free models)** | **Local: Ollama in Colab** |
|---|---|---|---|---|
| Model to use | `openai/gpt-oss-20b` (or `gpt-oss-120b`: same limits, smarter, half the speed) | `gemini-3.5-flash-lite` | `google/gemma-4-26b-a4b-it:free` | `qwen3:4b-instruct` (2.5 GB) |
| Free limits | 30 req/min · 1,000 req/day · **8K tokens/min** · 200K tokens/day. **Per account** (Groq "organization"), same for all 3 free chat models | **Not published any more** (only visible inside AI Studio). Unofficial reports: 10–15 req/min · 500 req/day · 250K tokens/min, **per Google Cloud project**. **Failed requests count too** (official) | 20 req/min · **50 req/day per account**, and **failed requests count too**. 1,000/day only after buying ≥ 10 credits (costs money) | None: each student runs their own model |
| What that means for one student | About 1–2 questions/min (TPM is the limit) and about 50 questions/day (TPD) | About 2–3 questions/min, 100–160 questions/day | About 10–16 questions per **day** | Limited only by speed |
| Tool calling | Yes, native and JSON mode. gpt-oss cannot make parallel calls | Yes, native, through the OpenAI-compatible endpoint (Google calls it beta) | Yes, for Gemma 4 (14 free models support tools) | Yes: **10/10** in our test, both native and plain JSON |
| OpenAI-compatible `base_url` | `https://api.groq.com/openai/v1` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `https://openrouter.ai/api/v1` | `http://localhost:11434/v1` |
| Students can sign up from Saudi Arabia? | **Yes.** Groq Limited (Riyadh) is the contracting party for customers in KSA, and no restriction was found. Login with Google, GitHub or email. No phone or card mentioned | **Yes.** Saudi Arabia is on Google's official list (in Colab, the VM's region is what counts). Google account, no card. Google may ask for age verification by ID or credit card. **A new Google account can need phone verification**, and Google limits accounts per phone number, so set up before the day | **Probably.** The Terms list no blocked countries. Email, Google or GitHub; the phone option is switched off | No account needed |
| Minimum age | **18** | **18** (under-18 school Workspace accounts are blocked) | **18** | none |
| Network round-trip from Saudi Arabia (measured, no model work) | ~0.47 s | 0.7–1.5 s | 0.5–0.8 s | 0 |
| Model latency (independent benchmark from the US, ~1K-token prompt) | **0.19 s** to first token, ~840 tokens/s, so **≈ 2 s per agent question** | **4.7 s** to first token (its "thinking" is counted in that time), so **≈ 20 s per question** | OpenRouter's own figures for Gemma 4 free: 0.9 s typical, **8 s at the slow end** (p95) | **Measured here:** ≈ 4.8 s per RAG call on a GTX 1060 |
| Our own latency test with a key | Pending a key | Pending a key | Pending a key | Done (table below) |
| Privacy | No training on prompts. Logs kept up to 30 days | Free-tier prompts are used to improve Google products, and human reviewers may read them | Depends on the free model's provider; the account may need an "allow training" switch on | Stays inside the student's VM |
| Biggest risk | 8K tokens/min per student, plus model churn (the free Llama models were shut down on 2026-08-16) | Limits are unpublished and were cut without notice. 503 overloads are reported. 18+ ID check | Daily cap far too low; Terms contradict the free tier | Free Colab may give no GPU. Each VM downloads about 4 GB (Ollama 1.5 GB plus the model 2.5 GB) |

> Secondary options checked briefly (Cerebras, GitHub Models, Mistral): see [Other providers](#other-providers) below.

## Local fallback: measured on this laptop

Each "per call" time is a realistic RAG prompt: about 1,300 input tokens and a short answer, with no prompt caching (`scripts/llm_probe.py`). The tool tests are 10 questions: 7 need a tool (calculator or deadline lookup) and 3 need no tool (`scripts/tool_format_test.py`).

| Model (Ollama tag) | Download | Licence | Per call, GPU | Tool test: plain JSON / JSON + 3 examples / native `tools=` | Verdict |
|---|---|---|---|---|---|
| `qwen3:4b-instruct` | 2.5 GB | Apache-2.0 | **4.8 s** | **10/10 · 10/10 · 10/10** | **Recommended (Colab GPU runtime)** |
| `qwen2.5:7b` | 4.7 GB | Apache-2.0 | 9.2 s (too big for this 6 GB card; fits a 16 GB T4) | 6/10 · 10/10 · 10/10 | Good, but bigger and slower |
| `qwen2.5:3b` | 1.9 GB | Qwen *Research* licence | 4.3 s | 10/10 · 10/10 · 9/10 | Avoid: non-Apache licence |
| `qwen2.5:1.5b` | 1.0 GB | Apache-2.0 | 3.1 s; **20 s CPU-only** | 8/10 · 8/10 · 7/10 | Emergency CPU option only |
| `qwen2.5:3b`, CPU-only with 2 threads (Colab's free CPU has 2) | | | **40 s** | n/a | Too slow for a 3-step agent |

What this means for the room:
- **The fallback needs a Colab GPU runtime.** Free Colab GPUs are "heavily restricted" and not guaranteed (Colab FAQ). Test on the morning of each session.
- **Every fresh Colab VM downloads Ollama (~1.5 GB) and the model (2.5 GB).** That happens over Google's network, not the room's wifi, and takes a few minutes.
- **Three Colab gotchas,** all handled in the T3 setup cell:
  - The Ollama installer needs `zstd`, which Colab lacks.
  - Colab has no systemd, so the server must be started by hand.
  - The default context is 4,096 tokens, and longer prompts are **silently cut**. Start the server with `OLLAMA_CONTEXT_LENGTH=8192`.
- **Do not run one shared Ollama server for the class from Colab.** Colab's rules forbid serving web services. Ollama also handles one request at a time by default, and with 4 simultaneous calls our test already reached p95 = 9.9 s.

## Tool-call format (input to T3)

The agent needs one tool-call format that works with **every** provider, including the local model. The test above compared:

- **Native `tools=`**: the provider parses the call. It scored 10, 10, 9 and 7 out of 10 across the four models. Wrong cases included calling a deadline tool for "Say thank you in Arabic" and answering deadline questions from memory.
- **Plain JSON in the reply**: our code parses `{"tool": ..., "args": ...}`.
  - With only a description, `qwen2.5:7b` did the arithmetic itself, and did it wrong (1234 × 5678 → "7006552"; the right answer is 7006652).
  - **With three short examples it scored 10/10 on three of the four models** (8/10 on the 1.5B).
- **Wording changes scores a lot.** One sentence ("only use a tool when needed") moved scores by 2–4 out of 10 in an earlier run.

**Decision for T3: plain JSON in the reply, with examples in the system prompt.**
- **It works on any chat model and any endpoint.** It doesn't depend on each provider's tool-calling implementation: Groq returns HTTP 400 on malformed tool calls, Ollama ignores `tool_choice`, and Gemini's layer is beta.
- **Students see every step:** raw reply → parse JSON → validate → run the tool. That is exactly what Session 3 teaches.
- **The failures are good teaching material.** Bad JSON, an invented tool name or a missing argument are what the validator (S3) and retries (S4) handle.
- **The prompt effect is a ready-made S3 demo:** 6/10 → 10/10 just from three examples.

## Other providers

| Provider | Status on 2026-11-02 | Usable for the class? |
|---|---|---|
| **GitHub Models** | **Retired** on 2026-07-30 (closed to new users on 2026-06-16) | No. Older tutorials using `models.github.ai` will fail |
| **Cerebras** | Free trial needs a **verified payment card** since 2026-07-16. One-time $5 credit expiring after 30 days; 5 req/min per account | No: needs a card |
| **Mistral** ("Free mode") | No card needed. Limits **not published** (shown only after sign-up). Prompts **used for training by default** (opt-out switch). Terms say the API is for "business customers"; minimum age 13 | Possible emergency backup; untested |
| **Colab built-in AI** (`google.colab.ai`) | Free for all Colab users, no key needed. Monthly limits not published; 18+ | No for the agent: it takes **one prompt only** (no system message, history or tools) and isn't an OpenAI-compatible endpoint we can point `base_url` at |

## What I could not verify, and how to check it

| Gap | Why | How to check (≈ time) |
|---|---|---|
| Real API latency and limits with a key | No keys yet | Put keys in `.env` (copy `.env.example`), then run `python scripts/llm_probe.py groq gemini openrouter --runs 5`. It prints latency plus a native and a JSON tool-call check (5 min) |
| Sign-up really works from Saudi Arabia | Needs a person, an 18+ account and a phone | One 18+ teammate signs up for Groq and Google AI Studio with a **personal** Gmail on a Saudi connection, and writes down any phone, ID or card prompts (15 min) |
| Gemini's real free limits | Shown only to signed-in users | After signing in, open `aistudio.google.com/rate-limit` and screenshot the Free tier row for `gemini-3.5-flash-lite` (2 min) |
| Colab GPU, driver and Ollama install | I can't run Colab | Run the T3 notebook `notebooks/00_setup.ipynb` on a fresh Colab **GPU** runtime and check that `ollama ps` shows "100% GPU" (10 min) |
| Colab works on the **venue Wi-Fi** | In late Oct 2026, some ISPs' DNS could not resolve Colab's runtime domain `*.prod.r.colab.dev` ("Unable to connect to the runtime") | Ask Tuwaiq IT to allow `*.prod.r.colab.dev`. Then connect a Colab notebook from the venue Wi-Fi a few days before Session 1 (5 min) |

## How these facts were checked

- **Research:** one research agent per topic read the providers' **own** pages and quoted them word for word, with URLs (below).
- **Fact-check:** a second, independent agent then re-read the sources and tried to **refute** every decision-critical claim. Corrections are already in this document.
  - **Groq:** 40 of 41 confirmed. The 41st, the name of a native tool-call error code, doesn't affect us.
  - **OpenRouter:** 38 of 40 confirmed. The other two were corrected: failed requests do count, and latency figures do exist.
  - **Gemini:** 34 of 39 confirmed. Four are the unofficial limit reports, labelled as such; the fifth is that Google does publish one speed figure (350 tokens/s). Added from the fact-check: failed requests count against the quota, and new Google accounts may need phone verification.
  - **Local model:** 40 of 41 confirmed. The other was about vLLM, which we don't use.
  - **Colab:** 38 of 40 confirmed. The other two were about pinning a runtime version, which doesn't affect this comparison. Added from the fact-check: the venue Wi-Fi/DNS check.
  - **Other providers:** 38 of 38 confirmed.
  - **Latency figures:** 39 of 40 confirmed. The other was a Cerebras limit, already ruled out above.
  - **FAISS vs ChromaDB (for T3):** 40 of 40 confirmed.
- **Unofficial figures are labelled as such:** Gemini's current limits and the independent latency benchmarks.

## Sources (read 2026-11-02)

**Groq:** [rate limits](https://console.groq.com/docs/rate-limits) · [models and prices](https://console.groq.com/docs/models) · [deprecations](https://console.groq.com/docs/deprecations) · [tool use](https://console.groq.com/docs/tool-use) · [OpenAI compatibility](https://console.groq.com/docs/openai) · [reasoning](https://console.groq.com/docs/reasoning) · [prompt caching](https://console.groq.com/docs/prompt-caching) · [your data](https://console.groq.com/docs/your-data) · [Services Agreement (18+, KSA entity)](https://console.groq.com/docs/legal/services-agreement) · [acceptable use](https://console.groq.com/docs/legal/ai-policy) · [billing FAQ (event credits)](https://console.groq.com/docs/billing-faqs)

**Google Gemini:** [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) · [pricing / free tier](https://ai.google.dev/gemini-api/docs/pricing) · [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) · [available regions](https://ai.google.dev/gemini-api/docs/available-regions) · [terms (18+, data use)](https://ai.google.dev/gemini-api/terms) · [Workspace accounts](https://ai.google.dev/gemini-api/docs/workspace) · [changelog](https://ai.google.dev/gemini-api/docs/changelog) · unofficial current limits: [Google forum, staff confirms Dec-2025 cut](https://discuss.ai.google.dev/t/111274) and [scriptbyai, 2026-10-19](https://www.scriptbyai.com/gemini-api-free-tier-limits/)

**OpenRouter:** [limits](https://openrouter.ai/docs/api-reference/limits) · [pricing (failed requests count)](https://openrouter.ai/pricing) · [model list API](https://openrouter.ai/api/v1/models) · [FAQ](https://openrouter.ai/docs/faq) · [terms (18+)](https://openrouter.ai/terms) · [Gemma 4 free page](https://openrouter.ai/google/gemma-4-26b-a4b-it:free)

**Local model and Colab:** [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) · [context length](https://docs.ollama.com/context-length) · [FAQ](https://docs.ollama.com/faq) · [GPU support](https://docs.ollama.com/gpu) · [install script](https://ollama.com/install.sh) · [qwen3 tags](https://ollama.com/library/qwen3/tags) · [qwen2.5 licences](https://ollama.com/library/qwen2.5) · [Colab FAQ](https://research.google.com/colaboratory/faq.html) · [Colab runtime versions](https://research.google.com/colaboratory/runtime-version-faq.html) · [Colab package list](https://github.com/googlecolab/backend-info) · [google.colab.ai source](https://github.com/googlecolab/colabtools/blob/main/google/colab/ai.py)

**Others:** [GitHub Models retirement](https://docs.github.com/en/github-models) · [Cerebras rate limits / trial](https://inference-docs.cerebras.ai/support/rate-limits) · [Mistral free mode](https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key)

**Independent latency benchmarks (not official):** [Artificial Analysis: gpt-oss-20b providers](https://artificialanalysis.ai/models/gpt-oss-20b/providers) · [gpt-oss-120b providers](https://artificialanalysis.ai/models/gpt-oss-120b/providers) · [Gemini 3.5 Flash-Lite](https://artificialanalysis.ai/models/gemini-3-5-flash-lite/providers). These are measured from a US data centre; a Colab VM is usually in the US too.
