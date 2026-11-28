"""
harness.py - the coding harness you use in Session 3 to build the RAG system.

You ask it for something in plain English; it reads the code, edits it, runs the checks, and
tells you what it did. The model never touches the filesystem itself: it replies with one JSON
object, and this file validates the request, runs it inside the repo, and sends the result back.

    python harness.py "Write read_file and load_documents in rag.py, then run run_check('rag')"
    python harness.py --print-prompt        # see exactly what the model is told

    import harness
    result = harness.run_agent("Write chunk_text and make_chunks in rag.py")
    print(result["answer"])

One request per run: each run starts fresh. Every step is printed while it works and logged
to logs/harness.jsonl. Review what it changed with `git diff rag.py`; undo with `git restore rag.py`.
It is the same loop as the one in Sessions 1-2 (tools, registry, limits, context, verification),
with tools for coding instead of tools for answering questions.

Why this harness is optimized for building RAG:
- the prompt states the RAG target (load -> chunk -> embed -> index -> retrieve ->
  answer with citations -> "I don't know") so the model keeps the goal in view
- the tools are the ones a coding agent needs: list, read, write, edit, run a check
- file reads and command output are cap ped, so the context stays small
- every tool error comes back as data the model can fix on the next step
- the loop stops on an answer, a step limit, a timeout, or an LLM error
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import config
import llm

# ---------------------------------------------------------------- settings
WORKSPACE = config.ROOT.resolve()  # the agent may only touch files inside this folder
MAX_STEPS = 30                     # a coding task needs more room than one Q&A turn
MAX_BLOCKED_ANSWERS = 3            # stop when it tries to finish this often without a passing check
TIMEOUT_SECONDS = 600              # give up on the whole task after this many seconds
MAX_HISTORY_MESSAGES = 10          # earlier messages kept for a follow-up task
MAX_CONTEXT_CHARS = 60_000         # hard cap on the conversation sent to the model
MAX_FILE_CHARS = 20_000            # cap on one read_file result
MAX_OUTPUT_CHARS = 4_000           # cap on one run_command result
COMMAND_TIMEOUT_SECONDS = 120      # cap on one command
# Longest reply the model may write in one step. run_agent() uses it while a task runs,
# then puts config.MAX_OUTPUT_TOKENS back.
# Note for students: choose the limit for the agent you are building:
#   - Q&A agent (agent.py): 800 (config.MAX_OUTPUT_TOKENS). Replies are short tool calls and answers.
#   - coding agent (this file): 8_000. Replies carry whole functions or files inside the JSON.
MAX_REPLY_TOKENS = 8_000
VERBOSE = True
LOG_FILE = config.ROOT / "logs" / "harness.jsonl"

# No shell: the model passes argv as a list, and only these programs are allowed.
ALLOWED_COMMANDS = {"python", "python3", "pytest", "git"}
GIT_READ_ONLY = {"status", "diff", "log", "show", "rev-parse"}
# Note for students: choose the git subcommands for what the agent may do:
#   - agent that only inspects the repo: status, diff, log, show, rev-parse (this list).
#   - agent that also manages branches: add "branch" (it can create and delete branches,
#     e.g. `git branch -D main`).
# Some options write files even in a read-only subcommand, e.g. `git diff --output=<file>`,
# so run_command() blocks these:
GIT_BLOCKED_OPTIONS = ("--output",)
PYTHON_NAMES = {"python", "python3"}
# Note for students: choose which Python runs the commands and checks:
#   - sys.executable (this file): the same interpreter and virtual environment as the
#     harness, so the checks see the workshop packages.
#   - plain "python": the first Python on the system PATH. Use it when that is the Python
#     you installed the workshop packages into.
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".venv-win"}
BLOCKED_FILES = {".env", ".env.local"}

# RAG-specific policy: the corpus and the evaluation set are read-only. The model may
# read them, but it may not change the data to make a check pass.
READ_ONLY_PATHS = ("data", "eval/questions.json")

# The standard checks for this workshop. run_check() returns a compact summary, so a
# failing run does not flood the context window. ("python" here becomes sys.executable,
# see PYTHON_NAMES above.)
CHECKS = {
    "smoke": ["python", "scripts/smoke_test.py"],
    # One check per Session 3 step, so a request for one step can be verified on its own. Exit code 0 only
    # when the check PASSES: a function left empty (TODO) keeps the harness from finishing.
    "load": ["python", "scripts/smoke_test.py", "--only", "Session 3: loading"],          # read_file, load_documents
    "chunks": ["python", "scripts/smoke_test.py", "--only", "Session 3: chunks"],         # chunk_text, make_chunks
    "search": ["python", "scripts/smoke_test.py", "--only", "Session 3: search"],         # embed ... search_docs
    "sections": ["python", "scripts/smoke_test.py", "--only", "Session 3: section"],      # split_sections, chunk_by_section
    "rag": ["python", "scripts/smoke_test.py", "--only", "Session 3: loading", "--only", "Session 3: chunks",
            "--only", "Session 3: search", "--only", "Session 3: section"],             # all of rag.py
    # answer.py, plus everything it needs (the last check asks the LLM one real question)
    "answer": ["python", "scripts/smoke_test.py", "--only", "Session 3"],
    "eval": ["python", "eval_runner.py"],
    "tests": ["python", "-m", "pytest", "-q"],
}

# A RAG harness should not trust "I changed it, it works". After the last edit, the
# model must run a check and see it pass before it may answer.
REQUIRE_CHECK_AFTER_EDIT = True

# Safety note: the workspace guard and the command allowlist are teaching boundaries,
# not an OS sandbox. `python` can still do anything the current user can do. Run the
# harness on a scratch checkout, and review the changes before you commit them.

SYSTEM_PROMPT = """You are a senior AI engineer working inside this repository:
{root}

Your job is to build the RAG system described in README.md. The target:
- load the documents in data/kfupm_raw (or the folder in CORPUS_DIR),
- split them into overlapping chunks,
- embed the chunks and build a searchable index,
- retrieve the best chunks for a question,
- answer only from those chunks, with citations like [01-05_Attendance_And_Withdrawal.txt#3],
- say "I don't know" when the documents do not contain the answer.

Work like an engineer:
1. Inspect before you edit: list_files, then read_file the files you need.
2. Find the TODO markers and the failing check.
3. Make one small change at a time: exactly ONE tool call per reply. The harness runs only the first.
   With edit_file, put the WHOLE TODO block in "old": the TODO comment AND the placeholder lines that
   belong to it (raise NotImplementedError(...), a "..." value, a stub loop), so no old code is left behind.
   Read the function again after editing it.
4. Run the check the request names (for example run_check('chunks')); otherwise the one that fits:
   'load', 'chunks', 'search', 'sections' or 'rag' for rag.py, 'answer' for answer.py, 'smoke' or 'eval'.
   Read the summary: a FAIL line says what broke.
5. Repeat until the check passes, then stop and summarize.

Rules:
- Never edit data/ or eval/questions.json: the harness makes them read-only. Never edit tests to make a check pass.
- Never weaken the citation or "I don't know" rules.
- Keep the code plain Python; do not add a framework.
- Stay inside {root}. Never read or write outside it.
- run_command only accepts these programs: {commands}. Pass argv as a list, never a shell string.
- After your last edit, run a check and see it pass before you answer.
- Follow the docstring and the comments of each function exactly: they are the specification. The harness rejects an answer that comes after an unverified edit.
- Use ask_rag to try the system on a real question when you need to see retrieval and citations.
- Keep the conversation small: do not paste whole files back to me.

Tools:
{tools}

Reply with ONE JSON object and nothing else.
To use a tool: {"tool": "<tool name>", "args": {...}}
To finish:     {"answer": "<what you changed and which checks passed>"}

Examples:
Task: What files are in the repo?
Reply: {"tool": "list_files", "args": {"path": "."}}
Task: Show me rag.py.
Reply: {"tool": "read_file", "args": {"filename": "rag.py"}}
Task: Implement chunk_text in rag.py.
Reply: {"tool": "read_file", "args": {"filename": "rag.py"}}
Task: The edit is in place. Run the smoke test.
Reply: {"tool": "run_check", "args": {"name": "smoke"}}
Task: Did the answer cite a source?
Reply: {"tool": "ask_rag", "args": {"question": "How long is one pomodoro?"}}
Task: Done.
Reply: {"answer": "Implemented chunk_text and search in rag.py; the smoke test passes."}"""


# ---------------------------------------------------------------- workspace guard
def resolve_path(filename, write=False):
    """Turn a model-supplied path into an absolute path inside WORKSPACE.
    Raises ValueError for anything that escapes the repository, points at secrets, or
    (for writes) tries to change the corpus or the evaluation set."""
    path = Path(filename)
    full = (path if path.is_absolute() else WORKSPACE / path).resolve()
    try:
        relative = full.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError(f"path must stay inside {WORKSPACE}: {filename}") from None
    if any(part in SKIP_DIRS for part in relative.parts):
        raise ValueError(f"path is not part of the project files: {filename}")
    if full.name in BLOCKED_FILES:
        raise ValueError(f"refusing to touch a secrets file: {filename}")
    if write:
        posix = relative.as_posix()
        if any(posix == read_only or posix.startswith(read_only + "/") for read_only in READ_ONLY_PATHS):
            raise ValueError(f"{posix} is read-only: do not change the corpus or the evaluation set")
    return full


# ---------------------------------------------------------------- tools
def list_files(path="."):
    """List the entries in a project directory."""
    folder = resolve_path(path)
    if not folder.is_dir():
        return {"ok": False, "error": f"not a directory: {path}"}
    entries = [
        {"name": entry.name + ("/" if entry.is_dir() else ""),
         "type": "dir" if entry.is_dir() else "file"}
        for entry in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        if entry.name not in SKIP_DIRS and entry.name not in BLOCKED_FILES
    ]
    return {"ok": True, "path": str(folder.relative_to(WORKSPACE)) or ".", "entries": entries}


def read_file(filename):
    """Read a UTF-8 file inside the project, capped so one file cannot flood the context.
    Returns the raw text, so the model can copy an exact `old` string into edit_file."""
    file = resolve_path(filename)
    if not file.is_file():
        return {"ok": False, "error": f"not a file: {filename}"}
    text = file.read_text(encoding="utf-8", errors="replace")
    return {
        "ok": True,
        "path": str(file.relative_to(WORKSPACE)),
        "lines": len(text.splitlines()),
        "truncated": len(text) > MAX_FILE_CHARS,
        "content": text[:MAX_FILE_CHARS],
    }


def write_file(filename, content):
    """Create or replace a UTF-8 file inside the project. The corpus and the evaluation
    set are read-only."""
    file = resolve_path(filename, write=True)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(file.relative_to(WORKSPACE)),
            "bytes": len(content.encode("utf-8"))}


def edit_file(filename, old, new):
    """Replace exactly one occurrence of `old` with `new`.
    Refusing an ambiguous edit is safer than guessing which one the model meant.
    The corpus and the evaluation set are read-only."""
    file = resolve_path(filename, write=True)
    if not file.is_file():
        return {"ok": False, "error": f"not a file: {filename}"}
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        return {"ok": False, "error": "old text not found; read the file again and copy the exact text"}
    if count > 1:
        return {"ok": False, "error": f"old text appears {count} times; include more surrounding context"}
    file.write_text(text.replace(old, new, 1), encoding="utf-8")
    return {"ok": True, "path": str(file.relative_to(WORKSPACE)),
            "bytes": len(new.encode("utf-8"))}


def run_command(argv, limit=MAX_OUTPUT_CHARS):
    """Run an allowlisted program inside the workspace, without a shell.
    Long output keeps its start and its END: errors and summaries are printed last."""
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        return {"ok": False, "error": "argv must be a non-empty list of strings"}
    program = Path(argv[0]).name
    if program not in ALLOWED_COMMANDS:
        return {"ok": False, "error": f"command not allowed: {argv[0]}; allowed: {sorted(ALLOWED_COMMANDS)}"}
    if program == "git" and (len(argv) < 2 or argv[1] not in GIT_READ_ONLY):
        return {"ok": False, "error": f"only read-only git subcommands are allowed: {sorted(GIT_READ_ONLY)}"}
    if program == "git" and any(part.startswith(GIT_BLOCKED_OPTIONS) for part in argv[2:]):
        return {"ok": False, "error": f"git options that write files are not allowed: {', '.join(GIT_BLOCKED_OPTIONS)}"}
    if program in PYTHON_NAMES:
        argv = [sys.executable, *argv[1:]]  # the harness's own Python (see PYTHON_NAMES)
    try:
        completed = subprocess.run(
            argv, cwd=WORKSPACE, capture_output=True, text=True,
            timeout=COMMAND_TIMEOUT_SECONDS, shell=False,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"command not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"command timed out after {COMMAND_TIMEOUT_SECONDS}s"}
    output = (completed.stdout + completed.stderr).strip()
    if limit and len(output) > limit:
        head = limit // 4
        output = (output[:head] + f"\n... ({len(output) - limit} chars cut from the middle) ...\n"
                  + output[-(limit - head):])
    return {"ok": completed.returncode == 0, "exit_code": completed.returncode,
            "output": output or "(no output)"}


def run_check(name):
    """Run one of the workshop checks and return only the lines that matter.
    This is the RAG-specific part: the harness knows how this repo is verified."""
    if name not in CHECKS:
        return {"ok": False, "error": f"unknown check {name!r}; use one of: {', '.join(CHECKS)}"}
    result = run_command(CHECKS[name], limit=None)  # filter the FULL output: the FAIL line is near the end
    output = result.get("output", "")
    markers = ("PASS", "FAIL", "TODO", "passed", "failed", "Passed", "Error", "error")
    summary = "\n".join(line for line in output.splitlines() if any(marker in line for marker in markers))
    return {
        "ok": result.get("ok", False),
        "check": name,
        "exit_code": result.get("exit_code"),
        "summary": (summary or output)[-3000:],
    }


def ask_rag(question):
    """Ask the RAG system a question and return its answer and cited sources.
    The fastest way to see whether retrieval and citations actually work."""
    try:
        import answer
        import rag
        result = answer.answer_question(rag.get_store(), question)
    except Exception as error:
        return {"ok": False, "error": f"{type(error).__name__}: {error}"}
    return {"ok": True, "question": question,
            "answer": result.get("answer"), "sources": result.get("sources", [])}


# ---------------------------------------------------------------- registry
TOOLS = {
    "list_files": {
        "function": list_files,
        "description": "List the entries in a project directory. Start with path '.'.",
        "args": {"path": str},
    },
    "read_file": {
        "function": read_file,
        "description": "Read a UTF-8 file inside the project. The content is the raw text for edit_file.",
        "args": {"filename": str},
    },
    "write_file": {
        "function": write_file,
        "description": "Create or replace a UTF-8 file inside the project.",
        "args": {"filename": str, "content": str},
    },
    "edit_file": {
        "function": edit_file,
        "description": "Replace one exact piece of text in an existing file. Prefer this over write_file.",
        "args": {"filename": str, "old": str, "new": str},
    },
    "run_command": {
        "function": run_command,
        "description": "Run an allowlisted program in the project root, e.g. python scripts/smoke_test.py.",
        "args": {"argv": list},
    },
    "run_check": {
        "function": run_check,
        "description": "Run a workshop check: 'load', 'chunks', 'search', 'sections' (one step of rag.py each), 'rag' (all of rag.py), 'answer' (answer.py), 'smoke' (everything), 'eval' (the question set) or 'tests'. Run the check the request names, after every edit.",
        "args": {"name": str},
    },
    "ask_rag": {
        "function": ask_rag,
        "description": "Ask the RAG system a question and see its answer and cited sources.",
        "args": {"question": str},
    },
}


def describe_tools():
    """One line per tool, for the system prompt."""
    lines = []
    for name, tool in TOOLS.items():
        args = ", ".join(f"{arg}: {kind.__name__}" for arg, kind in tool["args"].items())
        lines.append(f"- {name}({args}): {tool['description']}")
    return "\n".join(lines)


def validate_call(call):
    """Check a tool call before running it. Returns None when it is fine, or a message
    the model can read and fix."""
    if not isinstance(call, dict):
        return "a tool call must be a JSON object"
    name = call.get("tool")
    if name not in TOOLS:
        return f"unknown tool {name!r}; use one of: {', '.join(TOOLS)}"
    args = call.get("args", {})
    if not isinstance(args, dict):
        return '"args" must be a JSON object'
    expected = TOOLS[name]["args"]
    missing = [arg for arg in expected if arg not in args]
    extra = [arg for arg in args if arg not in expected]
    if missing:
        return f"missing argument(s): {', '.join(missing)}"
    if extra:
        return f"unknown argument(s): {', '.join(extra)}"
    for arg, kind in expected.items():
        value = args[arg]
        if kind is list:
            if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
                return f'"{arg}" must be a list of strings'
        elif not isinstance(value, kind):
            return f'"{arg}" must be a {kind.__name__}'
    return None


def run_tool(call):
    """Run one validated tool call. Tool errors come back as JSON data, so the loop
    can send them to the model instead of crashing."""
    try:
        output = TOOLS[call["tool"]]["function"](**call["args"])
    except Exception as error:
        output = {"ok": False, "error": f"{type(error).__name__}: {error}"}
    return json.dumps(output, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- prompt and protocol
def system_prompt():
    return (SYSTEM_PROMPT
            .replace("{root}", str(WORKSPACE))
            .replace("{commands}", ", ".join(sorted(ALLOWED_COMMANDS)))
            .replace("{tools}", describe_tools()))


def parse_reply(text):
    """Read the model's reply as one JSON object. Raises ValueError with a useful
    message when the reply is not one (the loop sends that message back)."""
    start = text.find("{")
    if start == -1:
        raise ValueError("your reply has no JSON object")
    try:
        # raw_decode reads the FIRST object and ignores the rest: a model that writes several
        # tool calls at once gets the first one run, instead of a "broken JSON" error for all.
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as error:
        raise ValueError(f"your JSON is broken ({error.msg})") from None
    if not isinstance(data, dict) or ("answer" not in data and "tool" not in data):
        raise ValueError('your JSON needs an "answer" key or a "tool" key')
    return data


# ---------------------------------------------------------------- observability
def log_event(event, **details):
    """Print one short line and append one JSON line to LOG_FILE."""
    if VERBOSE:
        print(f"  [{event}] " + " | ".join(f"{key}={str(value)[:150]}" for key, value in details.items()))
    LOG_FILE.parent.mkdir(exist_ok=True)
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **details}
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def trim_messages(messages, pinned=1):
    """Keep the first `pinned` messages and the newest others under MAX_CONTEXT_CHARS.
    run_agent() pins the system prompt, the history and the task, so the model never
    loses its goal. Never start with an orphan tool result: the model needs the request
    that caused it.
    Note for students: choose what to pin for the agent you are building:
      - short Q&A turns: pinned=1 (only the system prompt) is enough.
      - long coding tasks: pin the task too (run_agent() does), so the model keeps its
        goal after old tool output is trimmed away."""
    head, rest = messages[:pinned], messages[pinned:]
    kept, total = [], 0
    for message in reversed(rest):
        size = len(message.get("content", ""))
        if kept and total + size > MAX_CONTEXT_CHARS:
            break
        kept.append(message)
        total += size
    kept.reverse()
    if kept and kept[0]["role"] == "user" and kept[0]["content"].startswith("Tool result:"):
        kept.pop(0)
    return head + kept


# ---------------------------------------------------------------- the loop
def run_agent(task, history=None):
    """Give the model one coding task and run the tool loop until it answers.
    Returns a dict with: question, answer, sources (files changed), steps,
    tools_used, stopped, seconds, history."""
    # llm.chat() reads config.MAX_OUTPUT_TOKENS on every call. Raise it for this task only,
    # and put the Q&A value back afterwards (see MAX_REPLY_TOKENS).
    qa_limit = config.MAX_OUTPUT_TOKENS
    config.MAX_OUTPUT_TOKENS = max(qa_limit, MAX_REPLY_TOKENS)
    try:
        return _run_task(task, history)
    finally:
        config.MAX_OUTPUT_TOKENS = qa_limit


def _run_task(task, history):
    started = time.monotonic()
    messages = [{"role": "system", "content": system_prompt()}]
    messages += (history or [])[-MAX_HISTORY_MESSAGES:]
    messages.append({"role": "user", "content": task})
    pinned = len(messages)  # system prompt + history + task: trim_messages() never drops these
    log_event("task", task=task, provider=config.LLM_PROVIDER,
              model=config.PROVIDERS[config.LLM_PROVIDER]["model"])

    result = {"question": task, "answer": None, "sources": [], "steps": 0,
              "tools_used": [], "stopped": None, "seconds": 0, "history": []}
    last_edit_step = 0
    last_check = {"name": None, "ok": False, "step": 0}
    blocked = 0  # answers refused because no check passed after the last edit

    for step in range(1, MAX_STEPS + 1):
        if time.monotonic() - started > TIMEOUT_SECONDS:
            result["stopped"] = "timeout"
            break
        result["steps"] = step
        try:
            reply = llm.chat_with_retries(messages, log=lambda message: log_event("retry", message=message))
        except Exception as error:  # the LLM is unreachable even after retries
            log_event("llm_error", step=step, error=f"{type(error).__name__}: {error}")
            result["stopped"] = "llm_error"
            break
        messages.append({"role": "assistant", "content": reply})

        try:
            action = parse_reply(reply)
        except ValueError as error:  # bad JSON: tell the model and let it try again
            log_event("bad_json", step=step, reply=reply, error=str(error))
            messages.append({"role": "user", "content": f"Error: {error}. Reply with ONE JSON object."})
            continue

        if "answer" in action:
            if REQUIRE_CHECK_AFTER_EDIT and last_edit_step and not (last_check["ok"] and last_check["step"] > last_edit_step):
                log_event("blocked_answer", step=step, last_edit_step=last_edit_step, last_check=last_check)
                blocked += 1
                if blocked >= MAX_BLOCKED_ANSWERS:  # stuck: it keeps trying to finish without a passing check
                    result["stopped"] = "stuck"
                    result["answer"] = (f"Stopped: tried to finish {blocked} times, but check "
                                        f"{last_check['name']!r} did not pass after the last edit. Run it yourself "
                                        f"(python scripts/smoke_test.py) and read the FAIL or TODO line.")
                    break
                messages.append({"role": "user", "content": (
                    "Error: you edited the code after your last check. "
                    "Run the check for this request and make it pass before you answer."
                )})
                continue
            result["answer"] = str(action["answer"])
            result["stopped"] = "answer"
            break

        error = validate_call(action)
        if error:  # wrong tool call: send the error back so the model can fix it
            log_event("bad_tool_call", step=step, call=action, error=error)
            messages.append({"role": "user", "content": f"Error: {error}"})
            continue

        output = run_tool(action)
        result["tools_used"].append(action["tool"])
        try:
            tool_result = json.loads(output)
        except json.JSONDecodeError:
            tool_result = {}
        if action["tool"] in ("write_file", "edit_file") and tool_result.get("ok"):
            result["sources"].append(action["args"].get("filename"))
            last_edit_step = step
        if action["tool"] == "run_check":
            last_check = {"name": action["args"].get("name"), "ok": bool(tool_result.get("ok")), "step": step}
        log_event("tool", step=step, call=action, result=output)
        messages.append({"role": "user", "content": f"Tool result: {output}"})
        messages = trim_messages(messages, pinned)

    if result["stopped"] is None:  # the loop used all its steps without an answer
        result["stopped"] = "max_steps"
    if result["answer"] is None:
        result["answer"] = f"Stopped before finishing ({result['stopped']})."
    result["sources"] = list(dict.fromkeys(source for source in result["sources"] if source))
    result["seconds"] = round(time.monotonic() - started, 1)
    result["history"] = (history or []) + [
        {"role": "user", "content": task},
        {"role": "assistant", "content": json.dumps({"answer": result["answer"]}, ensure_ascii=False)},
    ]
    log_event("finish", stopped=result["stopped"], steps=result["steps"],
              tools=result["tools_used"], seconds=result["seconds"], answer=result["answer"])
    return result


# ---------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="A coding harness that builds the RAG system in this repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", nargs="?", help="the coding task, in plain English")
    parser.add_argument("--print-prompt", action="store_true", help="print the system prompt and exit")
    parser.add_argument("--quiet", action="store_true", help="hide the per-step log lines")
    parser.add_argument("--provider", choices=sorted(config.PROVIDERS),
                        help="LLM provider (default: LLM_PROVIDER in config.py)")
    parser.add_argument("--model", help="model name for the chosen provider")
    args = parser.parse_args(argv)

    if args.provider:
        config.LLM_PROVIDER = args.provider
    if args.model:
        config.PROVIDERS[config.LLM_PROVIDER]["model"] = args.model

    global VERBOSE
    VERBOSE = not args.quiet
    if args.print_prompt:
        print(system_prompt())
        return 0

    task = args.task or input("task> ").strip()
    if not task:
        parser.error("give a task, or run with --print-prompt")
    result = run_agent(task)
    print(f"\n{result['answer']}")
    return 0 if result["stopped"] == "answer" else 1


if __name__ == "__main__":
    sys.exit(main())
