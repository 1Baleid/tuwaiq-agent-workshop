"""
agent.py - Sessions 3-4: the harness loop. Fill in the short TODOs.

A model can only reply with text. This loop turns that text into work:
  1. send the question and the tools to the LLM
  2. read one JSON reply: {"tool": ...} or {"answer": ...}
  3. if it is a tool call, run it and send the result back
  4. stop at an answer, MAX_STEPS, or AGENT_TIMEOUT_SECONDS

run_agent() must return these keys: question, answer, sources, steps, tools_used,
stopped, seconds, history. The chat server and eval runner use them.
"""
import json
import time
from datetime import datetime

import answer
import config
import llm
import rag
import tools

# TODO 1-3: add these rules to the prompt below.
# 1. Call search_docs before answering a document question.
# 2. Cite sources like [course_credit.txt#3].
# 3. Answer "{i_dont_know}" when the tools cannot help.
SYSTEM_PROMPT = """You are a helpful assistant. Use the tools to answer questions.

{tools}

Rules:
- Use a tool when it helps; otherwise answer directly.

Reply with ONE JSON object and nothing else:
- tool call: {"tool": "<tool name>", "args": {...}}
- answer:    {"answer": "<your answer>"}
"""


def system_prompt():
    # .replace() is safer than .format(): the prompt is full of { } brackets
    return SYSTEM_PROMPT.replace("{tools}", tools.describe_tools()).replace("{i_dont_know}", answer.I_DONT_KNOW)


def parse_reply(text):
    """Read one JSON object from the model's reply."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("your reply has no JSON object")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("your JSON must be an object")
    # TODO 4: also require an "answer" or a "tool" key.
    return data


def log_event(event, **details):
    """Print a short line and keep a log file."""
    if config.VERBOSE:
        print(f"  [{event}] " + " | ".join(f"{key}={str(value)[:150]}" for key, value in details.items()))
    config.LOG_FILE.parent.mkdir(exist_ok=True)
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **details}
    # TODO 5: append json.dumps(record) as one line to config.LOG_FILE.


def run_agent(question, history=None):
    """Answer one question with the tools. Pass result["history"] to ask a follow-up."""
    started = time.monotonic()
    messages = [{"role": "system", "content": system_prompt()}]
    messages += (history or [])[-2 * config.MAX_HISTORY_TURNS:]  # keep the last few turns
    messages.append({"role": "user", "content": question})

    result = {"question": question, "answer": None, "sources": [], "steps": 0,
              "tools_used": [], "stopped": None, "seconds": 0, "history": []}

    for step in range(1, config.MAX_STEPS + 1):
        result["steps"] = step
        # TODO 6: stop with result["stopped"] = "timeout" when the task took too long.
        try:
            reply = llm.chat_with_retries(messages, log=lambda message: log_event("retry", message=message))
        except Exception as error:  # the LLM is unreachable even after retries
            log_event("llm_error", step=step, error=str(error))
            result["stopped"] = "llm_error"
            break
        messages.append({"role": "assistant", "content": reply})

        try:
            action = parse_reply(reply)
        except ValueError as error:  # bad JSON: tell the model and let it try again
            messages.append({"role": "user", "content": f"Error: {error}. Reply with one JSON object."})
            continue

        if "answer" in action:
            result["answer"] = str(action["answer"])
            result["stopped"] = "answer"
            break

        error = tools.validate_call(action)
        if error:  # wrong tool call: send the error back so the model can fix it
            messages.append({"role": "user", "content": f"Error: {error}"})
            continue

        # TODO 7: run the tool, record its name, and send the output back.
        raise NotImplementedError("TODO 7: run the tool, record its name, and send the output back")

    if result["stopped"] is None:  # the loop used all its steps without an answer
        result["stopped"] = "max_steps"
    if result["answer"] is None:
        result["answer"] = f"Sorry, I could not finish this question (stopped: {result['stopped']})."
    known_ids = {chunk["id"] for chunk in rag.get_store()["chunks"]}  # only real chunk ids
    result["sources"] = answer.cited_sources(result["answer"], known_ids)
    result["seconds"] = round(time.monotonic() - started, 1)
    # remember this turn so the next question can refer back
    result["history"] = (history or []) + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": json.dumps({"answer": result["answer"]}, ensure_ascii=False)},
    ]
    log_event("finish", stopped=result["stopped"], steps=result["steps"],
              tools=result["tools_used"], seconds=result["seconds"], answer=result["answer"])
    return result
