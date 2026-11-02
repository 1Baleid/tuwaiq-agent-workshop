"""
eval_runner.py - Session 5: run the evaluation set and see what fails.

    import eval_runner
    rows = eval_runner.run_eval()            # asks the agent every question in eval/questions.json
    eval_runner.results_table(rows)          # one row per question, failures in red

Each question in eval/questions.json looks like:
    {"id": "q1",
     "question": "How long is one pomodoro?",
     "expected_answer": "25 minutes",
     "source": "pomodoro_technique.txt",    # file that holds the answer; "tool:<name>" if a tool
                                            # gives it; null if the right answer is "I don't know"
     "keywords": ["25"]}                    # words the answer must contain; "a|b" means a OR b

Keywords let us mark answers automatically, without paying for another LLM call.
Run from a terminal:  python eval_runner.py
"""
import json
from datetime import datetime

import agent
import config


def load_questions(path=None):
    with open(path or config.EVAL_FILE, encoding="utf-8") as f:
        return json.load(f)


def check(result, question):
    """Mark one agent result. Returns (answer_ok, source_ok)."""
    text = result["answer"].lower()
    source = question["source"]
    if source is None:  # the right answer is "I don't know"
        return "i don't know" in text, not result["sources"]
    answer_ok = all(any(option.strip().lower() in text for option in keyword.split("|"))
                    for keyword in question["keywords"])
    if source.startswith("tool:"):  # the answer must come from a tool, e.g. "tool:get_deadline"
        return answer_ok, source.removeprefix("tool:") in result["tools_used"]
    cited_files = {source_id.split("#")[0] for source_id in result["sources"]}  # "x.txt#3" -> "x.txt"
    return answer_ok, source in cited_files


def run_eval(path=None):
    """Ask the agent every evaluation question. Returns one row (a dict) per question."""
    rows = []
    for question in load_questions(path):
        print(f"\n=== {question['id']}: {question['question']}")
        result = agent.run_agent(question["question"])
        answer_ok, source_ok = check(result, question)
        rows.append({
            "id": question["id"],
            "passed": answer_ok and source_ok,
            "answer_ok": answer_ok,
            "source_ok": source_ok,
            "question": question["question"],
            "answer": result["answer"],
            "expected": question["expected_answer"],
            "sources": ", ".join(result["sources"]),
            "tools": ", ".join(result["tools_used"]),
            "steps": result["steps"],
            "stopped": result["stopped"],
            "seconds": result["seconds"],
        })
        print("PASS" if rows[-1]["passed"] else "FAIL", f"({result['seconds']}s)")
    print(f"\nPassed {sum(row['passed'] for row in rows)} of {len(rows)}")
    return rows


def results_table(rows):
    """The results as a table; failed rows are shown in red (in Colab / Jupyter)."""
    import pandas as pd
    table = pd.DataFrame(rows)

    def color(row):
        style = "" if row["passed"] else "background-color: #fde2e2; color: #000"
        return [style] * len(row)

    return table.style.apply(color, axis=1)


def save_results(rows, label="run"):
    """Save the rows to results/eval_<label>_<date_time>.csv, to compare runs before and after a fix."""
    import pandas as pd
    path = config.ROOT / "results" / f"eval_{label}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    path.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"Saved {path.relative_to(config.ROOT)}")
    return path


if __name__ == "__main__":
    import pandas as pd

    rows = run_eval()
    save_results(rows)
    print(pd.DataFrame(rows)[["id", "passed", "answer_ok", "source_ok", "tools", "steps", "stopped", "seconds"]].to_string())
