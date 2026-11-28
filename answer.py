"""
answer.py - Session 3: RAG answers you can trust.

    question -> search_docs() -> numbered passages -> prompt -> LLM -> answer with [citations]
                                                                       or "I don't know"

The four functions marked EMPTY are built with the coding harness (harness.py), like rag.py:
their docstrings and comments are the specification. For example:

    python harness.py "Write format_passages and answer_naive in answer.py, then run run_check('answer')"

  Step 1  format_passages()    number the passages so they can be cited
  Step 2  answer_naive()       the first RAG answer, with and without RAG
  Step 3  extract_citations()  map [2] back to a real file, catch invented numbers
  Fix     answer()             the final function: score threshold + refusal rule
  Test    mini_test(), hit_at_k(), diagnose()   (given)

answer() must return {"answer": str, "citations": [{"n", "source", "chunk"}, ...], "passages": [...]}.

    import answer
    result = answer.answer("How many credit hours is normal full-time study in the US?")
    print(result["answer"], result["citations"])
"""
import json
import re
from pathlib import Path

import config
from llm import chat
from rag import search_docs

I_DONT_KNOW = "I don't know based on the documents."


def llm(prompt):
    """Send one prompt to the LLM and return its reply (no RAG: it answers from memory)."""
    return chat([{"role": "user", "content": prompt}])


# ---------------------------------------------------------------- Lab 1: label the passages
def format_passages(passages):
    """EMPTY: number the passages for the prompt, so the LLM can cite them as [1], [2], ...

    passages: the list from search_docs() (dicts with "source", "chunk", "text", ...).
    Returns: ONE str, the blocks joined with a blank line ("\n\n"). Each block is a header line, a new
    line, then the passage text. Numbering starts at 1:
        [1] (source: 01-05_Attendance_And_Withdrawal.txt, chunk 0)
        Article Nine: a student must attend ...

        [2] (source: 32_Transcripts_From_Outside_Dhahran.txt, chunk 1)
        Each transcript costs SAR 11.50 ...
    An empty list gives "".
    """
    # 1. For n, passage in enumerate(passages, start=1):
    #      block = f"[{n}] (source: {passage['source']}, chunk {passage['chunk']})\n{passage['text']}"
    # 2. Return "\n\n".join(blocks).
    raise NotImplementedError("write format_passages()")


# ---------------------------------------------------------------- Lab 2: prompt + LLM
# The LLM only sees this text: 1 instructions, 2 context (the passages), 3 the question.
# Given complete. Rule 2 makes citations possible; rule 3 is layer 2 of "I don't know" (see answer()).
PROMPT = """Use the passages below to answer the question.

Rules:
- Answer only from the passages, not from memory.
- Cite the passage number, like [2].
- If the passages do not contain the answer, reply exactly: {i_dont_know}

PASSAGES:
{passages}

QUESTION: {question}
ANSWER:"""


def build_prompt(question, passages):
    """Instructions + numbered passages + question, in one text."""
    # .replace() is safer than .format(): passages may contain { } brackets
    return (PROMPT.replace("{i_dont_know}", I_DONT_KNOW)
            .replace("{passages}", format_passages(passages))
            .replace("{question}", question))


def answer_naive(question, k=3):
    """EMPTY: search, then answer from the passages. No checks yet (no score threshold, no citations).

    Returns: the LLM's reply, one str.
    """
    # 1. passages = search_docs(question, k)      (the k best chunks; search_docs comes from rag.py)
    # 2. Return llm(build_prompt(question, passages)).
    raise NotImplementedError("write answer_naive()")


# ---------------------------------------------------------------- Lab 3: citations
def extract_citations(answer_text, passages):
    """EMPTY: find every [n] in the answer and map it back to its passage.

    Returns: a list of dicts, in the order the numbers first appear, each number once:
        "... 20% [1] ... [3] ... [1]"  ->  [{"n": 1, "source": "01-05_Attendance_And_Withdrawal.txt", "chunk": 0},
                                           {"n": 3, "source": ..., "chunk": ...}]
    "n" is an int. A number with no passage (0, or bigger than len(passages)) is NOT in the list: print
    the warning below for it instead, because the model made it up.
    """
    # 1. numbers = dict.fromkeys(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))   (in order, no repeats)
    # 2. For each n: if not 1 <= n <= len(passages):
    #        print(f"Warning: the answer cites [{n}], but there are only {len(passages)} passages: "
    #              "the model made it up.")
    #    and go on to the next number.
    # 3. Otherwise passage = passages[n - 1] (lists start at 0, citations at 1); append
    #    {"n": n, "source": passage["source"], "chunk": passage["chunk"]}.
    # 4. Return the list.
    raise NotImplementedError("write extract_citations()")


# ---------------------------------------------------------------- the fix: answer() with two layers of honesty
def answer(question, k=None):
    """EMPTY: search -> filter -> LLM -> cited answer, or "I don't know". Two layers of honesty:
    layer 1 (this code) skips the LLM when no passage is close enough; layer 2 (the prompt's last rule)
    makes the LLM say I_DONT_KNOW when the passages lack the answer.

    k: how many chunks to search for (None = config.TOP_K).
    Returns: a dict with exactly these keys (mini_test, diagnose, the smoke test and the chat use them):
        {"answer": str, "citations": [ {"n", "source", "chunk"}, ... ], "passages": [the passages used]}
    """
    # 1. passages = search_docs(question, k)
    # 2. Layer 1: keep only the passages with passage["score"] >= config.MIN_SCORE (read it here, every call).
    #    If none are left: return {"answer": I_DONT_KNOW, "citations": [], "passages": []} WITHOUT calling the LLM.
    # 3. reply = llm(build_prompt(question, passages))      (with the kept passages only)
    # 4. Return {"answer": reply, "citations": extract_citations(reply, passages), "passages": passages}.
    raise NotImplementedError("write answer()")


# ---------------------------------------------------------------- mini-test: does our assistant pass?
def load_tests():
    """The document questions of the evaluation set: [(question, expected file or None), ...].
    None means the right answer is "I don't know"."""
    with open(config.EVAL_FILE, encoding="utf-8") as f:
        questions = json.load(f)
    return [(q["question"], q["source"]) for q in questions
            if not (q["source"] or "").startswith("tool:")]  # tool questions are for the agent (Session 5)


def same_document(source, expected):
    """'01-05_Attendance.md' matches '01-05_Attendance': the .pdf, .md and .txt copies count as one document.
    expected may name several files, "a|b", when more than one document holds the answer."""
    return any(Path(source).stem == Path(option).stem for option in expected.split("|"))


def passed(result, expected):
    """Pass = the expected file is among the citations, or the assistant says "I don't know"."""
    if expected is None:
        return "i don't know" in result["answer"].lower()
    return any(same_document(citation["source"], expected) for citation in result["citations"])


def mini_test(tests=None):
    """Run every test question through answer() and print pass / FAIL."""
    tests = tests or load_tests()
    score = 0
    for question, expected in tests:
        ok = passed(answer(question), expected)
        score += ok
        print(f"{'pass' if ok else 'FAIL':5} {question}  ->  {expected or 'I dont know'}")
    print(f"{score} of {len(tests)} passed")
    return score


def hit_at_k(question, expected, k=3):
    """Did search even find the right document in its top k?"""
    hits = search_docs(question, k)
    return any(same_document(p["source"], expected) for p in hits)


def diagnose(tests=None, k=None):
    """For every test: pass, or is the failure a retrieval problem or a generation problem?"""
    k = k or config.TOP_K
    for question, expected in tests or load_tests():
        if passed(answer(question, k), expected):
            verdict = "pass"
        elif expected and not hit_at_k(question, expected, k):
            verdict = "retrieval"   # search never found the file: fix chunking, the model or k
        else:
            verdict = "generation"  # the LLM had the right passage and still failed: fix the prompt
        print(f"{verdict:11} {question}")


# ---------------------------------------------------------------- for the harness (tools.py, agent.py)
# The agent cites chunk ids like [01-05_Attendance_And_Withdrawal.pdf#3] instead of passage numbers: an id stays
# the same across several searches, a number [2] does not.
def format_sources(hits):
    """Label each chunk with its id for the agent: '[01-05_Attendance_And_Withdrawal.pdf#3]\n<text>' ..."""
    return "\n\n".join(f"[{hit['id']}]\n{hit['text']}" for hit in hits)


def cited_sources(reply, known_ids):
    """Which chunks does the reply cite? Only ids that really exist count, in order, no repeats.
    (Footnote marks like [4] in the documents are not chunk ids, so they are ignored.)"""
    cited = re.findall(r"\[([^\[\]]+?#\d+)\]", reply)
    return list(dict.fromkeys(chunk_id for chunk_id in cited if chunk_id in known_ids))


def answer_question(store, question):
    """answer() in the older format {"answer", "sources": chunk ids, "hits"} (used by the smoke test)."""
    result = answer(question)
    ids = [f"{c['source']}#{c['chunk']}" for c in result["citations"]]
    return {"answer": result["answer"], "sources": ids, "hits": result["passages"]}
