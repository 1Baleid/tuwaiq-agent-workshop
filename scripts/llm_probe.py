"""
llm_probe.py - quick health check of an LLM provider (instructor tool).

For each provider it reports:
  * latency for a RAG-sized prompt (~1,100 input tokens, short answer):
    time to first token (TTFT), total time, output tokens per second
  * native tool calling: does the API return a structured `tool_calls` field?
  * JSON tool calls: does the model follow the plain-JSON format our agent uses?

Usage (from the repo root):
  python scripts/llm_probe.py                   # the provider set in config.py
  python scripts/llm_probe.py groq gemini       # several providers
  python scripts/llm_probe.py local --runs 5    # more runs = steadier numbers
  python scripts/llm_probe.py local --model qwen2.5:1.5b
"""
import argparse
import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `import config` works
import config  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from openai import BadRequestError, OpenAI  # noqa: E402

load_dotenv()

# A RAG-sized prompt: 8 short documents (~1,100 tokens) and one question.
PASSAGE = (
    "The student services office handles enrolment letters, ID cards and fee questions. "
    "It is open Sunday to Thursday from 8:00 to 15:00. Requests sent by email are answered "
    "within three working days. Students must bring their university ID. Late fee payments "
    "are charged 50 SAR per week, up to 200 SAR. "
)
CONTEXT = "\n\n".join(f"[doc{i}.txt] {PASSAGE * 2}" for i in range(1, 9))


def rag_messages():
    # A unique tag at the START stops servers from reusing a cached copy of the prompt,
    # so every call pays the full prompt cost, like a new student question would.
    tag = uuid.uuid4().hex[:8]
    return [
        {"role": "system", "content": f"[{tag}] Answer using only the documents. Cite the document name in brackets."},
        {"role": "user", "content": f"Documents:\n{CONTEXT}\n\nQuestion: What is the maximum late fee?"},
    ]


# The same rule and the same calculator tool, described two ways.
RULE = "Never do arithmetic in your head: always use the calculator tool."
QUESTION = "What is 1234 * 5678?"
CALCULATOR_TOOL = {  # 1) the provider's native tool-calling format
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression, e.g. '12 * (3 + 4)'.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
}
JSON_SYSTEM = RULE + """

You can use one tool:
- calculator(expression: str): evaluate an arithmetic expression.

Reply with ONE JSON object and nothing else.
To use a tool: {"tool": "calculator", "args": {"expression": "..."}}
To answer:     {"answer": "..."}"""  # 2) plain JSON in the reply text (works with any model)


def make_client(name):
    """Return (client, model, options) for a provider in config.PROVIDERS; raise if the key is missing."""
    p = config.PROVIDERS[name]
    key = os.environ.get(p["key_name"]) if p["key_name"] else "not-needed"
    if not key:
        raise RuntimeError(f"no {p['key_name']} in .env or environment")
    # max_retries=0: we want to SEE rate-limit errors, not have the SDK hide them.
    client = OpenAI(base_url=p["base_url"], api_key=key, max_retries=0, timeout=120)
    return client, p["model"], p.get("options", {})


def timed_call(client, model, options):
    """One streamed call. Returns (seconds to first token, total seconds, output tokens)."""
    kwargs = dict(model=model, messages=rag_messages(), max_tokens=300, stream=True, **options)
    start = time.perf_counter()
    try:
        stream = client.chat.completions.create(**kwargs, stream_options={"include_usage": True})
    except BadRequestError:  # a few providers reject stream_options
        stream = client.chat.completions.create(**kwargs)
    first, text, usage = None, "", None
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            first = first or time.perf_counter() - start
            text += chunk.choices[0].delta.content
        usage = getattr(chunk, "usage", None) or usage
    total = time.perf_counter() - start
    tokens = usage.completion_tokens if usage else max(1, len(text) // 4)  # ~4 characters per token
    return first or total, total, tokens


def parse_json_reply(text):
    """Take the {...} part of a reply (models sometimes wrap it in ```json fences)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in reply: {text[:80]!r}")
    return json.loads(text[start:end + 1])


def check_native_tools(client, model, options):
    resp = client.chat.completions.create(
        model=model, max_tokens=500, tools=[CALCULATOR_TOOL], **options,
        messages=[{"role": "system", "content": RULE}, {"role": "user", "content": QUESTION}],
    )
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        return "FAIL: no tool call"
    args = json.loads(calls[0].function.arguments)
    return "ok" if calls[0].function.name == "calculator" and "expression" in args else f"FAIL: {calls[0].function}"


def check_json_tools(client, model, options):
    resp = client.chat.completions.create(
        model=model, max_tokens=500, **options,
        messages=[{"role": "system", "content": JSON_SYSTEM}, {"role": "user", "content": QUESTION}],
    )
    reply = parse_json_reply(resp.choices[0].message.content or "")
    ok = reply.get("tool") == "calculator" and "expression" in reply.get("args", {})
    return "ok" if ok else f"FAIL: {reply}"


def short_error(e):
    return f"FAIL: {type(e).__name__}: {str(e)[:120]}"


def probe(name, runs, model_override=None):
    client, model, options = make_client(name)
    model = model_override or model
    timed_call(client, model, options)  # warm-up: loads a local model / opens the connection (not counted)
    samples = [timed_call(client, model, options) for _ in range(runs)]
    ttft = statistics.median(s[0] for s in samples)
    total = statistics.median(s[1] for s in samples)
    speed = statistics.median(s[2] / max(s[1] - s[0], 1e-6) for s in samples)
    checks = []
    for check in (check_native_tools, check_json_tools):
        try:
            checks.append(check(client, model, options))
        except Exception as e:  # report it, keep going
            checks.append(short_error(e))
    return f"| {name} | {model} | {runs} | {ttft:.2f} | {total:.2f} | {speed:.0f} | {checks[0]} | {checks[1]} |"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("providers", nargs="*", default=[config.LLM_PROVIDER])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", help="override the model from config.py")
    args = parser.parse_args()

    print("| provider | model | runs | TTFT p50 (s) | total p50 (s) | output tok/s | native tools | JSON tools |")
    print("|---|---|---|---|---|---|---|---|")
    for name in args.providers:
        try:
            print(probe(name, args.runs, args.model), flush=True)
        except Exception as e:
            print(f"| {name} | - | - | - | - | - | {short_error(e)} | - |", flush=True)


if __name__ == "__main__":
    main()
