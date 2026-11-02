"""
tool_format_test.py - which tool-call format does a model follow reliably? (instructor tool)

Asks 10 questions: 7 need a tool (calculator or deadline lookup), 3 need no tool.
Each question is tried with three formats:
  json      plain JSON in the reply, described in words
  json_ex   the same, plus 3 short examples   <- the format our agent uses
  native    the provider's own `tools=` field

Usage (from the repo root):
  python scripts/tool_format_test.py                     # provider from config.py
  python scripts/tool_format_test.py local --model qwen2.5:1.5b
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `import config` works
import config  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

load_dotenv()

RULES = ("You are a helpful assistant for students. Never do arithmetic in your head: use the calculator tool. "
         "For any question about a deadline or date, use the get_deadline tool. "
         "Only use a tool when the question really needs it; for greetings or thanks, just answer.")
JSON_FORMAT = """

Tools:
- calculator(expression: str): evaluate an arithmetic expression.
- get_deadline(name: str): look up the date of a named deadline or event and how many days are left.

Reply with ONE JSON object and nothing else.
To use a tool: {"tool": "<tool name>", "args": {...}}
To answer:     {"answer": "<your answer>"}"""
EXAMPLES = """

Examples:
Question: What is 12 * 7?
Reply: {"tool": "calculator", "args": {"expression": "12 * 7"}}
Question: When does registration open?
Reply: {"tool": "get_deadline", "args": {"name": "registration opens"}}
Question: Hello!
Reply: {"answer": "Hello! How can I help you?"}"""
NATIVE_TOOLS = [
    {"type": "function", "function": {
        "name": "calculator", "description": "Evaluate an arithmetic expression, e.g. '12 * (3 + 4)'.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "get_deadline", "description": "Look up the date of a named deadline or event and how many days are left.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
]

# (question, the tool it should call; None = answer directly)
CASES = [
    ("What is 1234 * 5678?", "calculator"),
    ("The late fee is 50 SAR per week. How much is it for 7 weeks?", "calculator"),
    ("What is 15% of 2400?", "calculator"),
    ("Add 3.75, 4.5 and 12.25.", "calculator"),
    ("When is the add/drop deadline?", "get_deadline"),
    ("How many days are left until the final exam?", "get_deadline"),
    ("What's the deadline for the scholarship application?", "get_deadline"),
    ("Hi! Who are you?", None),
    ("Say thank you in Arabic.", None),
    ("Thanks, that's all.", None),
]
REQUIRED_ARG = {"calculator": "expression", "get_deadline": "name"}


def ask(client, model, options, fmt, question):
    """Return (tool name or None, args or None) for one question in one format."""
    if fmt == "native":
        reply = client.chat.completions.create(
            model=model, max_tokens=500, tools=NATIVE_TOOLS, **options,
            messages=[{"role": "system", "content": RULES}, {"role": "user", "content": question}],
        ).choices[0].message
        if reply.tool_calls:
            call = reply.tool_calls[0].function
            return call.name, json.loads(call.arguments)
        return None, None
    system = RULES + JSON_FORMAT + (EXAMPLES if fmt == "json_ex" else "")
    text = client.chat.completions.create(
        model=model, max_tokens=500, **options,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": question}],
    ).choices[0].message.content or ""
    reply = json.loads(text[text.find("{"): text.rfind("}") + 1])  # the {...} part of the reply
    return (reply["tool"], reply.get("args")) if "tool" in reply else (None, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("provider", nargs="?", default=config.LLM_PROVIDER)
    parser.add_argument("--model", help="override the model from config.py")
    args = parser.parse_args()

    p = config.PROVIDERS[args.provider]
    key = os.environ.get(p["key_name"]) if p["key_name"] else "not-needed"
    if not key:
        sys.exit(f"Missing {p['key_name']}: add it to .env (see .env.example).")
    client = OpenAI(base_url=p["base_url"], api_key=key, max_retries=0, timeout=120)
    model = args.model or p["model"]
    print(f"{args.provider} / {model}")

    for fmt in ("json", "json_ex", "native"):
        correct, notes = 0, []
        for question, expected in CASES:
            try:
                tool, tool_args = ask(client, model, p.get("options", {}), fmt, question)
                ok = tool == expected and (expected is None or bool((tool_args or {}).get(REQUIRED_ARG[expected])))
                if not ok:
                    notes.append(f"   wrong: {question!r} -> {tool or 'answered directly'} {tool_args or ''}")
            except Exception as e:  # bad JSON, API error, ...
                ok = False
                notes.append(f"   error: {question!r} -> {type(e).__name__}: {str(e)[:80]}")
            correct += ok
        print(f"{fmt:8} {correct}/{len(CASES)} correct")
        for note in notes:
            print(note)


if __name__ == "__main__":
    main()
