"""
tools.py - Session 3: the tool registry.

A tool is a normal Python function that the agent may ask us to run. The LLM cannot run
code; it can only write a request such as

    {"tool": "calculator", "args": {"expression": "50 * 3"}}

The registry (TOOLS) lists every tool with a description and its arguments, so we can
  1. tell the LLM which tools exist   -> describe_tools()
  2. check each request before running it -> validate_call()
  3. run it                           -> run_tool()

Tools here: search_docs (Sessions 1-2 as a tool), calculator and get_deadline.
"""
import ast
import csv
import operator
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict
import answer
import config
import rag
# ---------------------------------------------------------------- tool 1: document search
def resolve_abs_path(path_str: str) -> Path:
    """
    Resolve a relative or absolute path, allowing access only inside the project.
    """
    root = config.ROOT.resolve()
    path = Path(path_str)
    full_path = (path if path.is_absolute() else root / path).resolve()
    try:
        full_path.relative_to(root)
    except ValueError:
        raise ValueError(f"path must stay inside the project directory: {root}") from None
    return full_path

def read_file_tool(filename: str) -> Dict[str, Any]:
    """
    Read a UTF-8 file inside the project.
    :param filename: The name of the file to read.
    :return: Its absolute path and full text content.
    """
    # TODO (Session 3): read a UTF-8 project file and return its absolute path and content
# ---------------------------------------------------------------- tool 2: calculator

def list_files_tool(path: str) -> Dict[str, Any]:
    """
    List the entries in a project directory.
    :param path: The path to a directory to list files from.
    :return: The absolute directory path and its entries.
    """
 #TODO (Session 3): list directory entries with their names and file/directory types

def edit_file_tool(filename: str, content: str) -> Dict[str, Any]:
    """Replace the contents of an existing UTF-8 file inside the project."""
    #TODO (Session 3): replace the contents of an existing UTF-8 project file
# SOLUTION END
# ---------------------------------------------------------------- tool 2: document search
def search_docs(query):
    """Search the documents (the index from Session 1) and return the best chunks, labelled."""
    hits = [hit for hit in rag.search(rag.get_store(), query) if hit["score"] >= config.MIN_SCORE]
    if not hits:
        return "No matching documents."
    return answer.format_sources(hits)


# ---------------------------------------------------------------- tool 2: calculator
OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def calculator(expression):
    """Work out an arithmetic expression such as '12 * (3 + 4)'.
    We never use eval(): it would let the LLM run any Python code it likes."""

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("exponent too large")
            return OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.operand))
        raise ValueError(f"'{ast.unparse(node)}' is not allowed; use numbers and + - * / ** ( )")

    result = evaluate(ast.parse(expression, mode="eval").body)
    return round(result, 6) if isinstance(result, float) else result


# ---------------------------------------------------------------- tool 3: deadline lookup
def load_deadlines():
    """Read deadlines.csv from the corpus folder: {name: row}, each row with 'date' and 'note'."""
    with open(config.CORPUS_DIR / "deadlines.csv", encoding="utf-8") as f:
        return {row["name"]: row for row in csv.DictReader(f)}


def find_deadline(name, deadlines):
    """The deadline called `name`, ignoring upper/lower case ("final exams begin" finds
    "Final exams begin"), or None if there is none."""
    for known in deadlines:
        if known.lower() == name.strip().lower():
            return known
    return None


def parse_date(text):
    """Read a date written as YYYY-MM-DD, e.g. 2026-11-26."""
    return datetime.strptime(text, "%Y-%m-%d").date()


def get_deadline(name):
    """Find a deadline by name and say how many days are left."""
    deadlines = load_deadlines()
    found = find_deadline(name, deadlines)
    if found is None:
        return f"No deadline called '{name}'."
    row = deadlines[found]
    try:
        day = parse_date(row["date"])
    except ValueError:
        return f"The date of '{found}' in deadlines.csv is not a valid YYYY-MM-DD date."
    days_left = (day - date.today()).days
    note = f" {row['note']}." if row.get("note") else ""
    return f"{row['name']}: {day:%A %d %B %Y} ({days_left} days from today).{note}"


# ---------------------------------------------------------------- the registry
TOOLS = {
  #TODO (Session 3): register every tool with its function, description, and argument types
}


def describe_tools():
    """One line per tool, for the system prompt, e.g. '- calculator(expression: str): ...'."""
    lines = []
    for name, tool in TOOLS.items():
        args = ", ".join(f"{arg}: {kind.__name__}" for arg, kind in tool["args"].items())
        lines.append(f"- {name}({args}): {tool['description']}")
    return "\n".join(lines)


def validate_call(call):
    """Check a tool call from the LLM before we run it.
    Returns None when it is fine, or an error message the LLM can read and fix."""
    # TODO (Session 3): check the tool name, that args is a dict, and that the arguments match TOOLS
    return None  # no checks yet: every call is accepted


def run_tool(call):
    """Run one (already validated) tool call. Errors inside the tool come back as text,
    so the agent can read them instead of crashing."""
    tool = TOOLS[call["tool"]]
    try:
        return str(tool["function"](**call["args"]))
    except Exception as e:
        return f"Error from {call['tool']}: {e}"
