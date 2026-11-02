"""Tests for scripts/make_main.py. Run:  python tests/test_make_main.py   (or: pytest tests)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from make_main import strip_notebook, strip_solutions  # noqa: E402

SOLVED = '''def add(a, b):
    """Add two numbers."""
    # SOLUTION START: TODO (Session 1): return the sum
    return a + b
    # SOLUTION END


def retry():
    # SOLUTION START: TODO (Session 4): add retries
    for _ in range(3):
        pass
    # SOLUTION ELSE
    # return "no retries yet"  # keeps running on main
    # SOLUTION END


def keep():
    # SOLUTION START: TODO: remove this check
    check()
    # SOLUTION ELSE
    # SOLUTION END
    return 1
'''

EXPECTED = '''def add(a, b):
    """Add two numbers."""
    # TODO (Session 1): return the sum
    raise NotImplementedError('TODO (Session 1): return the sum')


def retry():
    # TODO (Session 4): add retries
    return "no retries yet"  # keeps running on main


def keep():
    # TODO: remove this check
    return 1
'''


def test_blocks_are_replaced():
    assert strip_solutions(SOLVED) == EXPECTED


def test_text_without_markers_is_unchanged():
    text = "x = 1  # SOLUTION is just a word here\n"
    assert strip_solutions(text) == text


def test_hint_without_todo_gets_prefix():
    out = strip_solutions("    # SOLUTION START: split it\n    pass\n    # SOLUTION END\n")
    assert out == "    # TODO: split it\n    raise NotImplementedError('TODO: split it')\n"


def test_broken_markers_raise():
    for bad in ["# SOLUTION START\nx = 1\n",
                "x = 1\n# SOLUTION END\n",
                "# SOLUTION START\n# SOLUTION START\n# SOLUTION END\n"]:
        try:
            strip_solutions(bad)
        except ValueError:
            continue
        raise AssertionError(f"no error for: {bad!r}")


def test_notebook_cells_and_outputs():
    notebook = {"cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# SOLUTION START stays in markdown"]},
        {"cell_type": "code", "metadata": {}, "execution_count": 3, "outputs": [{"output_type": "stream"}],
         "source": ["x = 1\n", "# SOLUTION START: TODO: set y\n", "y = 2\n", "# SOLUTION END\n"]},
    ], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    out = json.loads(strip_notebook(json.dumps(notebook)))
    code = out["cells"][1]
    assert "".join(code["source"]) == "x = 1\n# TODO: set y\nraise NotImplementedError('TODO: set y')\n"
    assert code["outputs"] == [] and code["execution_count"] is None
    assert out["cells"][0]["source"] == ["# SOLUTION START stays in markdown"]


def test_repo_files_convert():
    """Every .py and .ipynb file in the repo must have balanced markers."""
    root = Path(__file__).resolve().parent.parent
    for path in [*root.glob("*.py"), *root.glob("scripts/*.py"), *root.glob("notebooks/*.ipynb")]:
        if path.name == "make_main.py":
            continue
        text = path.read_text(encoding="utf-8")
        (strip_notebook if path.suffix == ".ipynb" else strip_solutions)(text, path.name)


if __name__ == "__main__":
    tests = [value for name, value in dict(globals()).items() if name.startswith("test_")]
    for test in tests:
        test()
        print("ok  ", test.__name__)
    print(f"{len(tests)} tests passed")
