"""
agent.py - Sessions 3 and 4: the agent loop (the "harness").

The LLM cannot run anything; it can only reply with text. This loop does the work:
  1. send the question and the list of tools to the LLM
  2. read the reply: a tool call {"tool": ..., "args": ...} or a final {"answer": ...}
  3. check the tool call, run it, send the result back to the LLM, and go to 2
  4. stop at an answer, after MAX_STEPS LLM calls, or after AGENT_TIMEOUT_SECONDS

    import agent
    result = agent.run_agent("When do final exams begin?")
    print(result["answer"])
"""
import json
import time
from datetime import datetime

import answer
import config
import llm
import rag
import tools

SYSTEM_PROMPT = """You are a helpful assistant for students. You answer questions with these tools:
{tools}

Rules:
- Never answer from memory. For every question that is not a greeting, a calculation or a date,
  call search_docs first, then answer only from what it returns.
- Never do arithmetic in your head: use the calculator tool.
- For a question about a deadline, an exam, an event or a date, call get_deadline.
- After each fact from the documents, cite its source exactly as labelled, like [course_credit.txt#3].
- If the tools cannot answer the question, reply {"answer": "{i_dont_know}"}

Reply with ONE JSON object and nothing else.
To use a tool: {"tool": "<tool name>", "args": {...}}
To answer:     {"answer": "<your answer, with [source] citations>"}

Examples:
Question: What is a credit hour?
Reply: {"tool": "search_docs", "args": {"query": "credit hour"}}
Question: Who founded the student union?
Reply: {"tool": "search_docs", "args": {"query": "student union founder"}}
Question: What is 12 * 7?
Reply: {"tool": "calculator", "args": {"expression": "12 * 7"}}
Question: When does registration open?
Reply: {"tool": "get_deadline", "args": {"name": "registration opens"}}
Question: Hello!
Reply: {"answer": "Hello! How can I help you?"}"""


def system_prompt():
    # .replace() instead of .format(): the JSON examples above are full of { } brackets
    return SYSTEM_PROMPT.replace("{tools}", tools.describe_tools()).replace("{i_dont_know}", answer.I_DONT_KNOW)


def parse_reply(text):
    """Read the LLM's reply as one JSON object. Raises ValueError if it is not one.
    Models sometimes wrap the JSON in ```json fences or add words around it,
    so we take the part from the first '{' to the last '}'."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("your reply has no JSON object")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"your JSON is broken ({e.msg})") from None
    if not isinstance(data, dict) or ("answer" not in data and "tool" not in data):
        raise ValueError('your JSON needs an "answer" key or a "tool" key')
    return data


def log_event(event, **details):
    """Record what the agent does: print a short line (if VERBOSE) and keep a log file."""
    if config.VERBOSE:
        print(f"  [{event}] " + " | ".join(f"{key}={str(value)[:150]}" for key, value in details.items()))
    # SOLUTION START: TODO (Session 4): also append {"time": ..., "event": event, **details} as ONE JSON line to config.LOG_FILE
    config.LOG_FILE.parent.mkdir(exist_ok=True)
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **details}
    with open(config.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    # SOLUTION ELSE
    # SOLUTION END


def run_agent(question, history=None):
    """Answer one question with the tools.
    `history` = earlier messages of this conversation (pass result["history"] to ask a follow-up).
    Returns a dict: answer, sources, steps, tools_used, stopped (why the loop ended), seconds, history."""
    started = time.monotonic()
    messages = [{"role": "system", "content": system_prompt()}]
    messages += (history or [])[-2 * config.MAX_HISTORY_TURNS:]  # keep only the last few turns (context size)
    messages.append({"role": "user", "content": question})
    log_event("question", question=question, provider=config.LLM_PROVIDER)

    result = {"question": question, "answer": None, "sources": [], "steps": 0, "tools_used": [], "stopped": None}
    for step in range(1, config.MAX_STEPS + 1):
        # SOLUTION START: TODO (Session 4): stop (result["stopped"] = "timeout") when more than config.AGENT_TIMEOUT_SECONDS have passed
        if time.monotonic() - started > config.AGENT_TIMEOUT_SECONDS:
            result["stopped"] = "timeout"
            break
        # SOLUTION ELSE
        # SOLUTION END
        result["steps"] = step
        try:
            reply = llm.chat_with_retries(messages, log=lambda message: log_event("retry", message=message))
        except Exception as e:  # the LLM is unreachable even after retries
            log_event("llm_error", step=step, error=f"{type(e).__name__}: {e}")
            result["stopped"] = "llm_error"
            break
        messages.append({"role": "assistant", "content": reply})
        # SOLUTION START: TODO (Session 3): parse the reply; if it has "answer", finish; otherwise validate the tool call, run it, and send the result back
        try:
            action = parse_reply(reply)
        except ValueError as e:  # bad JSON: tell the LLM what is wrong and let it try again
            log_event("bad_json", step=step, reply=reply, error=str(e))
            messages.append({"role": "user", "content": f"Error: {e}. Reply with ONE JSON object."})
            continue
        if "answer" in action:
            result["answer"] = str(action["answer"])
            result["stopped"] = "answer"
            break
        error = tools.validate_call(action)
        if error:  # wrong tool call: send the error back so the LLM can fix it
            log_event("bad_tool_call", step=step, call=action, error=error)
            messages.append({"role": "user", "content": f"Error: {error}"})
            continue
        output = tools.run_tool(action)
        result["tools_used"].append(action["tool"])
        log_event("tool", step=step, call=action, result=output)
        messages.append({"role": "user", "content": f"Tool result: {output}"})
        # SOLUTION END

    if result["stopped"] is None:  # the loop used all its steps without an answer
        result["stopped"] = "max_steps"
    if result["answer"] is None:
        result["answer"] = f"Sorry, I could not finish this question (stopped: {result['stopped']})."
    known_ids = {chunk["id"] for chunk in rag.get_store()["chunks"]}
    result["sources"] = answer.cited_sources(result["answer"], known_ids)
    result["seconds"] = round(time.monotonic() - started, 1)
    # Remember only the question and the final answer for follow-up questions (Session 4: state).
    # The answer is stored as JSON, the same format we ask the LLM to reply in.
    result["history"] = (history or []) + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": json.dumps({"answer": result["answer"]}, ensure_ascii=False)},
    ]
    log_event("finish", stopped=result["stopped"], steps=result["steps"], tools=result["tools_used"],
              seconds=result["seconds"], answer=result["answer"])
    return result
