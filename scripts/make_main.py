"""
make_main.py - build the `main` branch (code with TODOs) from the `solutions` branch.

We only ever edit `solutions`. Code that students should write is wrapped in markers:

    # SOLUTION START: TODO (Session 1): cut the text into chunks
    ...the solution...
    # SOLUTION END

On `main` that block becomes:

    # TODO (Session 1): cut the text into chunks
    raise NotImplementedError('TODO (Session 1): cut the text into chunks')

When the program must still run without the solution, add a SOLUTION ELSE part. Its lines
are commented out on `solutions` and become real code on `main`:

    # SOLUTION START: TODO (Session 4): retry failed calls
    ...the solution...
    # SOLUTION ELSE
    # return chat(messages)  # no retries yet
    # SOLUTION END

This works in .py files and in the code cells of .ipynb notebooks (whose outputs are
cleared on main). Every other file is copied unchanged, so the branches never drift.

Usage (from the repo root, on `solutions`, with everything committed):
    python scripts/make_main.py                  # add one commit to `main` (created if missing)
    python scripts/make_main.py --check          # exit 1 if `main` differs from what we would generate
    python scripts/make_main.py --show rag.py    # print the `main` version of one file
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = re.compile(r"^(?P<indent>[ \t]*)# SOLUTION START:?[ \t]*(?P<hint>.*?)\s*$")
ELSE = re.compile(r"^[ \t]*# SOLUTION ELSE\s*$")
END = re.compile(r"^[ \t]*# SOLUTION END\s*$")
SKIP = {"scripts/make_main.py", "tests/test_make_main.py"}  # these files talk ABOUT the markers


def strip_solutions(text, where="text"):
    """Return the `main` version of Python source: every SOLUTION block replaced by its TODO."""
    lines = text.splitlines(keepends=True)
    out, i = [], 0
    while i < len(lines):
        start = START.match(lines[i])
        if not start:
            if ELSE.match(lines[i]) or END.match(lines[i]):
                raise ValueError(f"{where} line {i + 1}: SOLUTION ELSE/END without SOLUTION START")
            out.append(lines[i])
            i += 1
            continue
        indent, hint = start["indent"], start["hint"] or "write this part"
        if not hint.upper().startswith("TODO"):
            hint = "TODO: " + hint
        else_part, j = None, i + 1
        while j < len(lines) and not END.match(lines[j]):
            if START.match(lines[j]):
                raise ValueError(f"{where} line {j + 1}: SOLUTION START inside another SOLUTION block")
            if ELSE.match(lines[j]):
                else_part = []
            elif else_part is not None:
                else_part.append(lines[j])
            j += 1
        if j == len(lines):
            raise ValueError(f"{where} line {i + 1}: SOLUTION START without SOLUTION END")
        out.append(f"{indent}# {hint}\n")
        if else_part is None:
            out.append(f"{indent}raise NotImplementedError({hint!r})\n")
        else:  # uncomment the ELSE lines: drop the first "# " after the indentation
            out += [re.sub(r"^([ \t]*)# ?", r"\1", line, count=1) for line in else_part]
        i = j + 1
    return "".join(out)


def strip_notebook(text, where="notebook"):
    """The `main` version of a notebook: SOLUTION blocks stripped in code cells, outputs cleared."""
    notebook = json.loads(text)
    for number, cell in enumerate(notebook["cells"], start=1):
        if cell["cell_type"] == "code":
            source = strip_solutions("".join(cell["source"]), f"{where} cell {number}")
            cell["source"] = source.splitlines(keepends=True)
            cell["outputs"] = []
            cell["execution_count"] = None
    return json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"


def main_version(path, data):
    """Bytes of `path` as they should be on `main`."""
    if path in SKIP:
        return data
    if path.endswith(".py"):
        return strip_solutions(data.decode("utf-8"), path).encode("utf-8")
    if path.endswith(".ipynb"):
        return strip_notebook(data.decode("utf-8"), path).encode("utf-8")
    return data


def git(*args, cwd=ROOT):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.decode(errors='replace')}")
    return result.stdout.decode("utf-8", errors="replace")


def committed(ref, path):
    """The bytes of `path` as stored in git at `ref` (not the copy on disk)."""
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout


def generate():
    """{path: bytes} for every file of the current commit, converted for `main`."""
    paths = [p for p in git("ls-tree", "-r", "--name-only", "-z", "HEAD").split("\0") if p]
    return {path: main_version(path, committed("HEAD", path)) for path in paths}


def check(files):
    """True if the `main` branch holds exactly `files`."""
    on_main = set(git("ls-tree", "-r", "--name-only", "-z", "main").split("\0")) - {""}
    ok = True
    for path in sorted(on_main ^ set(files)):
        print(f"only on {'main' if path in on_main else 'solutions'}: {path}")
        ok = False
    for path in sorted(on_main & set(files)):
        if committed("main", path) != files[path]:
            print(f"differs: {path}")
            ok = False
    return ok


def write_main(files, message):
    """Replace everything on `main` with `files` and commit, using a temporary worktree."""
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "main"
        if git("branch", "--list", "main").strip():
            git("worktree", "add", "--quiet", str(tree), "main")
        else:  # first run: start an empty main branch
            git("worktree", "add", "--quiet", "--orphan", "-b", "main", str(tree))
        try:
            for path in [p for p in git("ls-files", "-z", cwd=tree).split("\0") if p]:
                (tree / path).unlink()
            for path, data in files.items():
                (tree / path).parent.mkdir(parents=True, exist_ok=True)
                (tree / path).write_bytes(data)
            git("add", "--all", cwd=tree)
            if git("status", "--porcelain", cwd=tree).strip():
                git("commit", "--quiet", "-m", message, cwd=tree)
                print(f"main updated: {git('log', '-1', '--format=%h %s', 'main').strip()}")
            else:
                print("main is already up to date")
        finally:
            git("worktree", "remove", "--force", str(tree))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only compare; exit 1 if main is out of date")
    parser.add_argument("--show", metavar="FILE", help="print the main version of one file")
    parser.add_argument("-m", "--message", help="commit message for main")
    args = parser.parse_args()

    if args.show:
        path = Path(args.show).as_posix()
        sys.stdout.reconfigure(encoding="utf-8")
        print(main_version(path, (ROOT / path).read_bytes()).decode("utf-8"), end="")
        return
    if git("rev-parse", "--abbrev-ref", "HEAD").strip() != "solutions":
        sys.exit("Run this on the 'solutions' branch.")
    if git("status", "--porcelain").strip():
        sys.exit("Commit (or stash) your changes first: main is built from the last commit.")
    files = generate()
    if args.check:
        ok = check(files)
        print("main is in sync with solutions" if ok else "main is OUT OF DATE: run python scripts/make_main.py")
        sys.exit(0 if ok else 1)
    sha = git("rev-parse", "--short", "HEAD").strip()
    write_main(files, args.message or f"Generate main from solutions {sha}")


if __name__ == "__main__":
    main()
