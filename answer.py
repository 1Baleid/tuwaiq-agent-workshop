"""
answer.py - Session 2: answers you can trust.

Find the best chunks, give them to the LLM labelled with their id, and get back an answer that
cites them, like "A credit is about 15 hours of class [course_credit.txt#3]", or "I don't know"
when the documents do not contain the answer.

    import rag, answer
    store = rag.build_store()
    result = answer.answer_question(store, "Who created the Pomodoro Technique?")
    print(result["answer"], result["sources"])
"""
import re

import config
import llm
import rag

I_DONT_KNOW = "I don't know based on the documents."

SYSTEM_PROMPT = f"""You answer questions using ONLY the sources you are given.
After each fact, cite its source exactly as it is labelled, like [course_credit.txt#3].
If the sources do not contain the answer, reply exactly: {I_DONT_KNOW}"""


def format_sources(hits):
    """Label each chunk with its id for the prompt: '[course_credit.txt#3]\n<text>' ..."""
    return "\n\n".join(f"[{hit['id']}]\n{hit['text']}" for hit in hits)


def build_messages(question, hits):
    """The chat messages for the LLM: the instructions, then the numbered sources and the question."""
    # SOLUTION START: TODO (Session 2): return [system message with SYSTEM_PROMPT, user message with format_sources(hits) and the question]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Sources:\n{format_sources(hits)}\n\nQuestion: {question}"},
    ]
    # SOLUTION END


def cited_sources(reply, known_ids):
    """Which chunks does the reply cite? Only ids that really exist count, in order, no repeats.
    (Footnote marks like [4] in the documents are not chunk ids, so they are ignored.)"""
    cited = re.findall(r"\[([^\[\]]+?#\d+)\]", reply)
    return list(dict.fromkeys(chunk_id for chunk_id in cited if chunk_id in known_ids))


def answer_question(store, question):
    """Answer a question from the documents. Returns {"answer", "sources", "hits"}."""
    hits = rag.search(store, question)
    # "I don't know", check 1: no chunk is close enough to the question, so don't even ask the LLM.
    # SOLUTION START: TODO (Session 2): if there are no hits, or the best score is below config.MIN_SCORE, return I_DONT_KNOW with no sources
    if not hits or hits[0]["score"] < config.MIN_SCORE:
        return {"answer": I_DONT_KNOW, "sources": [], "hits": hits}
    # SOLUTION ELSE
    # SOLUTION END
    # "I don't know", check 2: the prompt tells the LLM to say it when the sources lack the answer.
    reply = llm.chat(build_messages(question, hits))
    return {"answer": reply, "sources": cited_sources(reply, {hit["id"] for hit in hits}), "hits": hits}
