"""
smoke_test.py - is everything set up and working?

    python scripts/smoke_test.py            # every check (instructors, before a session)
    python scripts/smoke_test.py --quick    # setup only: Python, packages, embeddings, API key (pre-work)

In Colab, run it inside the notebook so it can read your key from Colab Secrets:
    import scripts.smoke_test as smoke
    smoke.main(["--quick"])

Each check prints PASS, FAIL (with a hint), or TODO. TODO means a session exercise is not
written yet, which is normal on the `main` branch. Exit code 1 if any check FAILs.
"""
import argparse
import importlib.metadata
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so `import config` works from any folder

# Expected versions from requirements.txt; pandas and scikit-learn are newer for Python 3.14 wheels.
EXPECTED = {"openai": "2.54.0", "python-dotenv": "1.2.4", "sentence-transformers": "5.7.0", "torch": "2.11.0",
            "numpy": "2.4.6", "pandas": "3.1.1", "scikit-learn": "1.9.1", "chromadb": "1.5.9", "pypdf": "6.21.4"}
state = {}  # things one check makes and a later check uses (the search store)


def check_python():
    version = ".".join(map(str, sys.version_info[:3]))
    note = "" if sys.version_info[:2] in ((3, 13), (3, 14)) else " (project setup targets Python 3.13 and 3.14)"
    return f"Python {version}{note}"


def check_packages():
    notes = []
    for package, expected in EXPECTED.items():
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            if package == "chromadb":  # rag.py falls back to numpy without it
                notes.append("chromadb missing (numpy search will be used)")
                continue
            raise RuntimeError(f"{package} is not installed. Run: pip install -r requirements.txt") from None
        if installed.split("+")[0] != expected:
            notes.append(f"{package} {installed} (expected {expected})")
    import numpy, openai, sentence_transformers  # noqa: E401, F401  (installed is not enough: they must import)
    return "all expected versions" if not notes else "OK, but: " + "; ".join(notes)


def check_embeddings():
    import config
    import rag
    vectors = rag.embed(["Hello", "Hi there"])
    similarity = float(vectors[0] @ vectors[1])
    return f"{config.EMBEDDING_MODEL}: {vectors.shape[1]} numbers per text; 'Hello' vs 'Hi there' = {similarity:.2f}"


def check_llm():
    import config
    import llm
    start = time.perf_counter()
    reply = llm.chat([{"role": "user", "content": "Reply with just the word OK."}])
    if not reply.strip():
        raise RuntimeError("the LLM sent an empty reply")
    provider = config.PROVIDERS[config.LLM_PROVIDER]
    return f"{config.LLM_PROVIDER} / {provider['model']} replied {reply.strip()[:30]!r} in {time.perf_counter() - start:.1f}s"


def check_loading():
    import config
    import rag
    documents = rag.load_documents()
    if not documents:
        raise RuntimeError(f"no .txt/.md/.pdf files in {config.CORPUS_DIR}")
    bad = next((d for d in documents if set(d) != {"source", "text"} or "/" in d["source"] or "\\" in d["source"]), None)
    if bad:
        raise RuntimeError(f"each document must be {{'source': file name only, 'text': ...}}; got keys {sorted(bad)}, "
                           f"source={bad.get('source')!r}")
    return f"{len(documents)} documents loaded"


def check_chunks():
    import rag
    example = rag.chunk_text("one two three four five six seven eight nine ten", 4, 1)  # chunk_text's docstring
    expected = ["one two three four", "four five six seven", "seven eight nine ten"]
    if example != expected:
        raise RuntimeError(f"chunk_text(...ten, 4, 1) should give {expected}, got {example}")
    chunks = rag.make_chunks(rag.load_documents())
    bad = next((c for c in chunks if c.get("id") != f"{c.get('source')}#{c.get('chunk')}"
                or not isinstance(c.get("chunk"), int)), None)
    if bad:  # answer.cited_sources() only accepts ids like "file.txt#3"
        raise RuntimeError(f"chunk ids must look like 'file.txt#3'; got {bad.get('id')!r}")
    return f"chunk_text matches its docstring example; {len(chunks)} chunks with ids like {chunks[0]['id']!r}"


SECTION_DOC = {"source": "01-05_Test_Doc.md", "text": "intro line\n## Rule A\nfirst rule\n## Rule B\nsecond rule"}
SECTION_CHUNKS = ["01-05 test doc: intro line", "01-05 test doc > Rule A: first rule", "01-05 test doc > Rule B: second rule"]


def check_sections():
    import config
    import rag
    got = rag.chunk_by_section(SECTION_DOC)
    if got != SECTION_CHUNKS:
        raise RuntimeError(f"chunk_by_section should give {SECTION_CHUNKS}, got {got}")
    before = config.CHUNK_BY_SECTION
    config.CHUNK_BY_SECTION = True
    try:
        texts = [c["text"] for c in rag.make_chunks([SECTION_DOC])]
    finally:
        config.CHUNK_BY_SECTION = before
    if texts != SECTION_CHUNKS:
        raise RuntimeError(f"with CHUNK_BY_SECTION = True, make_chunks must use chunk_by_section; got {texts}")
    return "chunk_by_section labels every section, and make_chunks uses it when CHUNK_BY_SECTION = True"


def check_answer_helpers():
    import answer
    import config
    passages = [{"source": "a.txt", "chunk": 0, "text": "first", "score": 0.9},
                {"source": "b.txt", "chunk": 4, "text": "second", "score": 0.8}]
    expected = "[1] (source: a.txt, chunk 0)\nfirst\n\n[2] (source: b.txt, chunk 4)\nsecond"
    got = answer.format_passages(passages)
    if got != expected:
        raise RuntimeError(f"format_passages should give {expected!r}, got {got!r}")
    got = answer.extract_citations("x [2] y [7] z [2] [1]", passages)
    want = [{"n": 2, "source": "b.txt", "chunk": 4}, {"n": 1, "source": "a.txt", "chunk": 0}]
    if got != want:
        raise RuntimeError(f"extract_citations should give {want} ([7] does not exist), got {got}")
    before = config.MIN_SCORE
    config.MIN_SCORE = 2.0  # no passage can reach it, so answer() must not even call the LLM
    try:
        result = answer.answer("anything at all")
    finally:
        config.MIN_SCORE = before
    if result != {"answer": answer.I_DONT_KNOW, "citations": [], "passages": []}:
        raise RuntimeError(f"answer() must return I_DONT_KNOW with no citations when no passage passes MIN_SCORE; got {result}")
    return "format_passages, extract_citations and the MIN_SCORE refusal work"


def check_search():
    import rag
    store = state["store"] = rag.get_store()  # the agent's search_docs tool reuses this store
    target = store["chunks"][len(store["chunks"]) // 2]  # a chunk from the middle of the corpus
    query = " ".join(target["text"].split()[:15])  # its first 15 words
    found = [hit["id"] for hit in rag.search(store, query)]
    if target["id"] not in found:
        raise RuntimeError(f"searching for words of {target['id']} did not find it (got {found})")
    return f"searching words from {target['id']} finds it"


def first_document_question():
    import config
    questions = json.loads(Path(config.EVAL_FILE).read_text(encoding="utf-8"))
    return next(q for q in questions if q["source"] and not q["source"].startswith("tool:"))


def check_rag_answer():
    import answer
    question = first_document_question()
    result = answer.answer_question(state["store"], question["question"])
    missing = [k for k in question["keywords"] if not any(o.lower() in result["answer"].lower() for o in k.split("|"))]
    if missing:
        raise RuntimeError(f"answer to {question['question']!r} lacks {missing}: {result['answer'][:150]!r}")
    return f"{question['question']!r} -> {result['answer'][:60]!r} sources={result['sources']}"


def check_tools():
    import tools
    assert tools.calculator("2 + 3 * 4") == 14, "calculator('2 + 3 * 4') should be 14"
    first_deadline = next(iter(tools.load_deadlines()))
    assert "days" in tools.get_deadline(first_deadline), "get_deadline did not find a known deadline"
    assert tools.validate_call({"tool": "calculator", "args": {"expression": "1+1"}}) is None
    if tools.validate_call({"tool": "no_such_tool", "args": {}}) is None:
        raise NotImplementedError("validate_call accepts unknown tools (TODO (Session 1))")
    return "calculator, get_deadline and validate_call work"


def check_agent():
    import agent
    import config
    config.VERBOSE = False
    state["store"]  # needs the search check to have passed
    result = agent.run_agent("What is 1234 * 5678?")
    if "7006652" not in result["answer"].replace(",", "") or "calculator" not in result["tools_used"]:
        raise RuntimeError(f"expected 7006652 via the calculator; got {result['answer'][:120]!r} "
                           f"tools={result['tools_used']} stopped={result['stopped']}")
    return f"1234 * 5678 = 7006652 via the calculator in {result['steps']} steps, {result['seconds']}s"


QUICK = [("Python version", check_python), ("Packages", check_packages),
         ("Embedding model (downloads ~90 MB once)", check_embeddings), ("LLM key and one call", check_llm)]
FULL = QUICK + [("Session 3: loading", check_loading), ("Session 3: chunks", check_chunks),
                ("Session 3: search", check_search),
                ("Session 3: section chunking", check_sections), ("Session 3: answer helpers", check_answer_helpers),
                ("Session 3: answer with citations", check_rag_answer), ("Session 1: tools", check_tools),
                ("Sessions 1-2: agent loop", check_agent)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check that the workshop setup works.")
    parser.add_argument("--quick", action="store_true", help="setup checks only (pre-work)")
    parser.add_argument("--only", action="append", metavar="NAME",
                        help="run only the checks whose name contains NAME (repeatable), e.g. --only 'Session 3'")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles may not print every character otherwise

    statuses = []
    checks = QUICK if args.quick else FULL
    if args.only:
        checks = [(name, check) for name, check in checks if any(part.lower() in name.lower() for part in args.only)]
    for name, check in checks:
        print(f"- {name}: ", end="", flush=True)
        start = time.perf_counter()
        try:
            status, detail = "PASS", check()
        except NotImplementedError as e:
            status, detail = "TODO", str(e)
        except KeyError as e:
            if e.args == ("store",):  # an earlier check (search) did not finish
                status, detail = "SKIP", "needs the search check to pass first"
            else:
                status, detail = "FAIL", f"KeyError: {e}"
        except Exception as e:
            status, detail = "FAIL", f"{type(e).__name__}: {e}"
        print(f"{status} ({time.perf_counter() - start:.1f}s) {detail}")
        statuses.append(status)
    failed = statuses.count("FAIL")
    print(f"\n{statuses.count('PASS')} passed, {failed} failed, {statuses.count('TODO')} TODO, "
          f"{statuses.count('SKIP')} skipped")
    print("All good!" if not failed else "Something is wrong: read the FAIL lines above. Students: see 'If something "
                                         "goes wrong' in the pre-work guide. Helpers: docs/known_errors.md.")
    # Exit code: 0 = every check passed, 1 = a check failed, 2 = no failure but work is left (TODO or SKIP).
    # Code 2 lets the coding harness (harness.py) see that the work is not finished yet.
    return 1 if failed else 2 if statuses.count("TODO") or statuses.count("SKIP") else 0


if __name__ == "__main__":
    sys.exit(main())
