"""
answer.py - Session 3: RAG answers you can trust. Fill in the short TODOs.

    question -> search_docs() -> numbered passages -> prompt -> LLM -> answer with [citations]
                                                                       or "I don't know"

  Lab 1  format_passages()    number the passages so they can be cited (TODO 1)
  Lab 2  answer_naive()       the first RAG answer, with and without RAG (TODO 2-3)
  Lab 3  extract_citations()  map [2] back to a real file, catch invented numbers (TODO 4-5)
  Break  answer()             the final function: score threshold + refusal rule (TODO 6-7)
  Test   mini_test(), hit_at_k(), diagnose()

answer() must return {"answer": str, "citations": [{"n", "source", "chunk"}, ...], "passages": [...]}.

    import answer
    result = answer.answer("How many credit hours is normal full-time study in the US?")
    print(result["answer"], result["citations"])
"""
import json
import re

import config
from llm import chat
from rag import search_docs

I_DONT_KNOW = "I don't know based on the documents."


def llm(prompt):
    """Send one prompt to the LLM and return its reply (no RAG: it answers from memory)."""
    return chat([{"role": "user", "content": prompt}])


# ---------------------------------------------------------------- Lab 1: label the passages
def format_passages(passages):
    """Number the passages for the prompt:
    [1] (source: 01-05_Attendance_And_Withdrawal.pdf, chunk 0)
    Article Nine: a student must attend ..."""
    blocks = []
    for n, passage in enumerate(passages, start=1):
        # TODO 1: add one f-string to blocks: "[n] (source: <source>, chunk <chunk>)", a new line, then the text.
        raise NotImplementedError("TODO 1: add one f-string per passage to blocks")
    return "\n\n".join(blocks)


# ---------------------------------------------------------------- Lab 2: prompt + LLM
# The LLM only sees this text: 1 instructions, 2 context (the passages), 3 the question.
# TODO 4 (Lab 3): add this rule to the prompt below:   - Cite the passage number, like [2].
# TODO 7 (planned break): add this rule too:
#   - If the passages do not contain the answer, reply exactly: {i_dont_know}
PROMPT = """Use the passages below to answer the question.

Rules:
- Answer only from the passages, not from memory.

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
    """Search, then answer from the passages. No checks yet."""
    # TODO 2: passages = the k best chunks for the question (search_docs).
    # TODO 3: return the LLM's reply to build_prompt(question, passages).
    raise NotImplementedError("TODO 2-3: search, then ask the LLM with build_prompt()")


# ---------------------------------------------------------------- Lab 3: citations
def extract_citations(answer_text, passages):
    """Find every [n] in the answer and map it to its passage.
    [1] -> {"n": 1, "source": "01-05_Attendance_And_Withdrawal.pdf", "chunk": 0}. A number with no passage is flagged."""
    citations = []
    numbers = dict.fromkeys(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))  # in order, no repeats
    for n in numbers:
        if not 1 <= n <= len(passages):
            print(f"Warning: the answer cites [{n}], but there are only {len(passages)} passages: "
                  "the model made it up.")
            continue
        # TODO 5: add {"n": n, "source": ..., "chunk": ...} to citations, taken from passage n (passages[n - 1]).
        raise NotImplementedError("TODO 5: map [n] back to its passage")
    return citations


# ---------------------------------------------------------------- the fix: answer() with two layers of honesty
def answer(question, k=None):
    """search -> filter -> LLM -> cited answer, or "I don't know"."""
    passages = search_docs(question, k)
    # Layer 1 (code): if no passage scores at least MIN_SCORE, don't even call the LLM.
    # TODO 6: keep only passages with score >= config.MIN_SCORE; if none are left,
    #         return {"answer": I_DONT_KNOW, "citations": [], "passages": []}.
    # Layer 2 (prompt): TODO 7 tells the LLM what to say when the passages lack the answer.
    reply = llm(build_prompt(question, passages))
    return {"answer": reply, "citations": extract_citations(reply, passages), "passages": passages}


# ---------------------------------------------------------------- mini-test: does our assistant pass?
def load_tests():
    """The document questions of the evaluation set: [(question, expected file or None), ...].
    None means the right answer is "I don't know"."""
    with open(config.EVAL_FILE, encoding="utf-8") as f:
        questions = json.load(f)
    return [(q["question"], q["source"]) for q in questions
            if not (q["source"] or "").startswith("tool:")]  # tool questions are for the agent (Session 5)


def passed(result, expected):
    """Pass = the expected file is among the citations, or the assistant says "I don't know"."""
    if expected is None:
        return "i don't know" in result["answer"].lower()
    return expected in {citation["source"] for citation in result["citations"]}


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
    return any(p["source"] == expected for p in hits)


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
