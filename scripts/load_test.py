"""
load_test.py - can the LLM handle the whole class at once? (instructor tool, ticket T2)

Two scenarios:
  shared : N students press "run" at the same moment, all using ONE key.
           N calls are sent at once (default N=30, change it with --n).
  burst  : ONE student asks a few questions in a row. Each agent question makes
           several calls (think -> tool -> tool -> answer), and the prompt grows at
           every step. Shows whether one student's own key stays inside its limits.

Every call is recorded as ok / 429 (rate limited) / other error, with its latency.
The run PASSES if the success rate and the p95 latency meet the targets below.

Usage (from the repo root):
  python scripts/load_test.py shared                    # provider from config.py, N=30
  python scripts/load_test.py shared --n 45
  python scripts/load_test.py burst --questions 3 --calls-per-question 4
  python scripts/load_test.py burst --provider local    # try the fallback without editing config.py
"""
import argparse
import asyncio
import json
import math
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `import config` works
import config  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI  # noqa: E402

load_dotenv(ROOT / ".env")

PASS_SUCCESS_RATE = 0.95  # at least 95% of calls must succeed ...
PASS_P95_SECONDS = 15     # ... and 95% of the successful calls must finish within 15 seconds

# Text that looks like retrieved document chunks (~180 tokens per document).
PASSAGE = (
    "The student services office handles enrolment letters, ID cards and fee questions. "
    "It is open Sunday to Thursday from 8:00 to 15:00. Requests sent by email are answered "
    "within three working days. Students must bring their university ID. Late fee payments "
    "are charged 50 SAR per week, up to 200 SAR. "
)


def new_question_tag():
    return uuid.uuid4().hex[:8]


def make_messages(question_tag, docs=6, earlier_steps=0):
    """A realistic agent prompt: the same instructions for everyone, ~1,200 tokens of documents
    for this question, and the earlier steps of the same question."""
    context = "\n\n".join(f"[doc{i}.txt] {PASSAGE * 2}" for i in range(1, docs + 1))
    messages = [
        {"role": "system", "content": "Answer using only the documents. Cite the document name in brackets."},
        # The tag makes every question different, as in class. The steps of ONE question share
        # their start, so a server's prompt cache helps exactly as much as it would for real.
        {"role": "user", "content": f"(question {question_tag})\nDocuments:\n{context}\n\n"
                                    "Question: What is the maximum late fee for 3 weeks?"},
    ]
    for _ in range(earlier_steps):  # each earlier step adds a tool call and its result
        messages.append({"role": "assistant", "content": '{"tool": "calculator", "args": {"expression": "50 * 3"}}'})
        messages.append({"role": "user", "content": "Tool result: 150"})
    return messages


async def one_call(client, model, options, messages, timeout):
    """Send one chat call and return what happened (never raises)."""
    start = time.perf_counter()
    result = {"status": "ok"}
    try:
        raw = await client.chat.completions.with_raw_response.create(
            model=model, messages=messages, max_tokens=300, timeout=timeout, **options
        )
        usage = raw.parse().usage
        result["tokens"] = usage.total_tokens if usage else None
        details = getattr(usage, "prompt_tokens_details", None)
        result["cached_tokens"] = getattr(details, "cached_tokens", None)  # tokens served from the prompt cache
        result["limits"] = {k: v for k, v in raw.headers.items() if k.lower().startswith("x-ratelimit")}
    except APIStatusError as e:  # the server answered with an error code
        result["status"] = "429" if e.status_code == 429 else f"http_{e.status_code}"
        result["retry_after"] = e.response.headers.get("retry-after")
        result["error"] = str(e)[:300]
    except APITimeoutError:
        result["status"] = "timeout"
    except APIConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = str(e)[:300]
    result["seconds"] = round(time.perf_counter() - start, 2)
    return result


async def run_shared(client, model, options, n, timeout):
    """N calls at exactly the same time, one key (N different students' questions)."""
    calls = (one_call(client, model, options, make_messages(new_question_tag()), timeout) for _ in range(n))
    return await asyncio.gather(*calls)


async def run_burst(client, model, options, questions, calls_per_question, timeout):
    """One student: questions one after another; each question = several calls in a row."""
    results = []
    for q in range(1, questions + 1):
        tag = new_question_tag()
        for step in range(calls_per_question):
            r = await one_call(client, model, options, make_messages(tag, earlier_steps=step), timeout)
            r.update(question=q, step=step + 1)
            results.append(r)
            print(f"  question {q} step {step + 1}: {r['status']} in {r['seconds']}s", flush=True)
    return results


def percentile(values, p):
    """Nearest-rank percentile: p=50 is the median, p=95 means 95% of values are at or below it."""
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(p / 100 * len(values)) - 1)]


def summarize(results, wall_seconds):
    ok = [r for r in results if r["status"] == "ok"]
    latencies = [r["seconds"] for r in ok]
    tokens = sum(r.get("tokens") or 0 for r in ok)
    cached = sum(r.get("cached_tokens") or 0 for r in ok)
    last_limits = next((r["limits"] for r in reversed(ok) if r.get("limits")), {})
    return {
        "calls": len(results),
        "ok": len(ok),
        "success_rate": round(len(ok) / len(results), 3) if results else 0,
        "rate_limited_429": sum(r["status"] == "429" for r in results),
        "other_errors": sorted({r["status"] for r in results if r["status"] not in ("ok", "429")}),
        "p50_seconds": percentile(latencies, 50),
        "p95_seconds": percentile(latencies, 95),
        "wall_seconds": round(wall_seconds, 1),
        "tokens_used": tokens,
        "of_which_cached": cached,
        "tokens_per_minute": round(tokens / wall_seconds * 60) if wall_seconds else None,
        "rate_limit_headers_last_seen": last_limits,
    }


async def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", choices=["shared", "burst"])
    parser.add_argument("--provider", default=config.LLM_PROVIDER, help="default: LLM_PROVIDER in config.py")
    parser.add_argument("--model", help="override the model from config.py")
    parser.add_argument("--n", type=int, default=30, help="shared: number of calls sent at once")
    parser.add_argument("--questions", type=int, default=3, help="burst: questions asked in a row")
    parser.add_argument("--calls-per-question", type=int, default=4, help="burst: LLM calls per question")
    parser.add_argument("--timeout", type=float, default=60, help="seconds before one call gives up")
    args = parser.parse_args()

    p = config.PROVIDERS[args.provider]
    key = os.environ.get(p["key_name"]) if p["key_name"] else "not-needed"
    if not key:
        sys.exit(f"Missing {p['key_name']}: add it to .env (see .env.example), then run again.")
    model = args.model or p["model"]
    # max_retries=0: we want to COUNT rate-limit errors, not have the SDK quietly retry them.
    client = AsyncOpenAI(base_url=p["base_url"], api_key=key, max_retries=0)

    print(f"Scenario '{args.scenario}' on {args.provider} / {model}")
    start = time.perf_counter()
    options = p.get("options", {})
    if args.scenario == "shared":
        results = await run_shared(client, model, options, args.n, args.timeout)
    else:
        results = await run_burst(client, model, options, args.questions, args.calls_per_question, args.timeout)
    summary = summarize(results, time.perf_counter() - start)
    passed = summary["success_rate"] >= PASS_SUCCESS_RATE and (summary["p95_seconds"] or 1e9) <= PASS_P95_SECONDS
    summary.update(provider=args.provider, model=model, scenario=args.scenario,
                   passed=passed, settings=vars(args), when=datetime.now().isoformat(timespec="seconds"))

    print(json.dumps({k: v for k, v in summary.items() if k != "settings"}, indent=2))
    errors = sorted({r.get("error", "")[:200] for r in results if r.get("error")})
    for e in errors[:3]:
        print("example error:", e)
    print("PASS" if passed else "FAIL",
          f"(targets: success >= {PASS_SUCCESS_RATE:.0%}, p95 <= {PASS_P95_SECONDS}s)")

    out = ROOT / "results" / f"load_{args.scenario}_{args.provider}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "calls": results}, indent=2), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
