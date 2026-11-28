"""
rag.py - Session 3: from documents to a searchable index.

    documents  ->  chunks  ->  embeddings  ->  index  ->  search_docs()

The functions below are EMPTY: you build them with the coding harness (harness.py). Each one has a
docstring (what it returns) and numbered comments (how): together they are the specification the
harness follows. One request per step works best, for example:

    python harness.py "Write read_file and load_documents in rag.py, then run run_check('load')"

  Step 1  read_file(), load_documents()        read every .md / .txt / .pdf file
  Step 2  chunk_text(), make_chunks()          cut texts into overlapping pieces of words
  Step 3  embed()                              turn text into meaning-vectors (compare with keyword_search())
  Step 4  numpy_search(), build_index()        search by hand, then a ChromaDB index
          search_docs()                        find the closest chunks, distance -> score
  Fix     split_sections(), chunk_by_section() one chunk per section, labelled with its heading

search_docs() must return a list of {"text", "source", "chunk", "score", "id"}, best first.
answer.py and the harness (tools.py) use it.

    import rag
    index = rag.build_index(rag.make_chunks(rag.load_documents()))
    for hit in rag.search_docs("Can I quit a class after the first week?", k=3, index=index):
        print(round(hit["score"], 2), hit["source"], hit["chunk"], hit["text"][:80])
"""
import glob
import os
import re
from pathlib import Path

import numpy as np

import config

try:
    import chromadb  # ChromaDB: a vector database
except ImportError:  # no chromadb on this computer: plain numpy below does the same job
    chromadb = None

_embedders = {}  # embedding models we already loaded, by name
_index = None    # the index get_index() built last


# ---------------------------------------------------------------- Lab 1: load
def read_file(path):
    """Return the text of one file, or None if this kind of file cannot be read.

    path: a str or Path. Returns: str, or None.
    """
    # 1. Turn `path` into a Path.
    # 2. If its suffix (lower case) is ".md" or ".txt": open it with encoding="utf-8" and return the whole text.
    # 3. If its suffix is ".pdf": from pypdf import PdfReader, and return the text of every page joined with
    #    "\n" (use page.extract_text() or "" for each page).
    # 4. Any other suffix: return None.
    raise NotImplementedError("write read_file()")


def load_documents(folder=None):
    """Read every document in a folder.

    folder: a folder path, or None for config.CORPUS_DIR (e.g. data/kfupm_raw). The documents are directly
    in this folder (there is no docs/ subfolder).
    Returns: a list of dicts, one per readable file, in file-name order:
        [{"source": "01-05_Attendance_And_Withdrawal.txt", "text": "Article Nine: ..."}, ...]
    "source" is the file name only (os.path.basename), never a full path.
    """
    # 1. folder = Path(folder or config.CORPUS_DIR)
    # 2. Loop over sorted(glob.glob(str(folder / "*"))) and call read_file(path) for each.
    # 3. If read_file returns None, remember the file name in a "skipped" list and go on.
    # 4. Otherwise append {"source": os.path.basename(path), "text": text}.
    # 5. Print f"Loaded {len(docs)} documents from {folder}", then one line per skipped file if any.
    # 6. Return the list.
    raise NotImplementedError("write load_documents()")


# ---------------------------------------------------------------- Lab 2: chunk
def chunk_text(text, chunk_size=None, overlap=None):
    """Cut a text into chunks of `chunk_size` words. Neighbouring chunks share `overlap` words.

    chunk_size: words per chunk (None = config.CHUNK_SIZE). overlap: shared words (None = config.CHUNK_OVERLAP).
    Returns: a list of str, each chunk being its words joined with one space. Empty text gives [].

    chunk_text("one two three four five six seven eight nine ten", 4, 1)
    -> ['one two three four', 'four five six seven', 'seven eight nine ten']
    """
    # 1. Fill in the defaults (overlap can be 0, so test "overlap is None", not "not overlap").
    # 2. If overlap >= chunk_size: raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE").
    # 3. words = text.split(); step = chunk_size - overlap.
    # 4. For start in range(0, len(words), step): add " ".join(words[start:start + chunk_size]);
    #    stop right after the chunk that reaches the end (start + chunk_size >= len(words)),
    #    so the last words never appear as an extra tiny chunk.
    raise NotImplementedError("write chunk_text()")


def make_chunks(documents):
    """Chunk every document. Each chunk remembers where it came from.

    documents: the list from load_documents().
    Returns: a list of dicts, numbered from 0 inside each document:
        {"id": "01-05_Attendance_And_Withdrawal.txt#0", "source": "01-05_Attendance_And_Withdrawal.txt",
         "chunk": 0, "text": "..."}
    The id MUST be exactly f"{source}#{number}" with a plain integer: the citation code only accepts ids
    like "file.txt#3" (never "file.txt#3-1").
    """
    # PLAY WITH THE CHUNKING: change these in config.py, then search again (the index rebuilds by itself).
    #   CHUNK_BY_SECTION  False = a word window that ignores the document's structure (chunk_text)
    #                     True  = one chunk per "## heading" section, with the heading in front (chunk_by_section)
    #   CHUNK_SIZE        words per window. With CHUNK_BY_SECTION = True, a section longer than this is cut
    #                     into pieces. In data/kfupm_structured, 240 of 253 sections fit in 120 words and the
    #                     longest has 167, so CHUNK_SIZE = 170 keeps every rule whole in one chunk.
    #                     Mind the limit: the embedding model reads only the first 256 tokens of a chunk, about
    #                     130 words of this text. 170 is still safe here (the longest section is 227 tokens),
    #                     but in a bigger window the words past the limit are never searched.
    #   CHUNK_OVERLAP     words two neighbouring windows share, so a sentence cut at a border survives.
    #   CORPUS_DIR        data/kfupm_structured (sections) or data/kfupm_raw (one plain dump of the same text).
    # Try: raw + word windows, structured + word windows, structured + sections; then CHUNK_SIZE 30 vs 300.
    # Compare which chunk search_docs() puts first for the same question.
    #
    # How to write this function:
    # 1. For each document, get its pieces (a list of str):
    #      config.CHUNK_BY_SECTION is True  -> pieces = chunk_by_section(doc)
    #      config.CHUNK_BY_SECTION is False -> pieces = chunk_text(doc["text"])
    #    Read config.CHUNK_BY_SECTION here, every call (students change it while the program runs).
    # 2. For number, text in enumerate(pieces): append the dict above.
    # 3. Return all chunks of all documents in one list.
    raise NotImplementedError("write make_chunks()")


# ---------------------------------------------------------------- Lab 3: embed
def embed(texts):
    """Turn texts into meaning-vectors: a numpy array with one row per text, dtype float32,
    each row of length 1 (normalized), so a dot product of two rows is their cosine similarity.

    texts: a list of str. Returns: np.ndarray of shape (len(texts), 384) for all-MiniLM-L6-v2.
    """
    # 1. name = config.EMBEDDING_MODEL.
    # 2. Load the model only once per name: keep it in the module dict _embedders.
    #    To load: from sentence_transformers import SentenceTransformer; SentenceTransformer(name).
    #    Before loading, hide the harmless HF_TOKEN warning:
    #      from huggingface_hub.utils import logging as hf_logging; hf_logging.set_verbosity_error()
    # 3. vectors = model.encode(texts, normalize_embeddings=True)
    # 4. Return np.asarray(vectors, dtype="float32").
    raise NotImplementedError("write embed()")


def similarity(text_a, text_b):
    """Cosine similarity of two texts: about 1 = same meaning, about 0 = unrelated."""
    a, b = embed([text_a, text_b])
    return float(a @ b)


def keyword_search(query, chunks, k=3):
    """The old way, to compare: count the words a chunk shares with the query.
    It has no idea that "quit" means "withdraw"."""
    query_words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for chunk in chunks:
        shared = query_words & set(re.findall(r"\w+", chunk["text"].lower()))
        scored.append({**chunk, "score": len(shared), "shared": sorted(shared)})
    return sorted(scored, key=lambda hit: -hit["score"])[:k]


# ---------------------------------------------------------------- Lab 4: index & search
def numpy_search(query, chunks, vectors, k=3):
    """Search by hand: compare the query with every chunk, sort, keep the top k.

    chunks: the list from make_chunks(). vectors: embed([chunk["text"] for chunk in chunks]).
    Returns: the k best chunks, best first, each a copy of the chunk dict plus "score" (a Python float):
        [{**chunk, "score": 0.71}, ...]
    """
    # 1. query_vector = embed([query])[0]
    # 2. scores = vectors @ query_vector   (one cosine similarity per chunk, in one numpy line)
    # 3. best = np.argsort(-scores)[:k]    (positions of the k highest scores)
    # 4. Return [{**chunks[i], "score": float(scores[i])} for i in best].
    raise NotImplementedError("write numpy_search()")


class NumpyCollection:
    """The same job as a Chroma collection, in plain numpy. Used only when chromadb is missing."""

    def add(self, ids, embeddings, documents, metadatas):
        self.ids, self.documents, self.metadatas = ids, documents, metadatas
        self.vectors = np.asarray(embeddings, dtype="float32")

    def count(self):
        return len(self.ids)

    def query(self, query_embeddings, n_results, where=None):
        rows = [i for i, meta in enumerate(self.metadatas)
                if not where or all(meta.get(key) == value for key, value in where.items())]
        distances = 1 - self.vectors[rows] @ np.asarray(query_embeddings[0], dtype="float32")
        best = [rows[i] for i in np.argsort(distances)[:n_results]]
        return {"ids": [[self.ids[i] for i in best]],
                "documents": [[self.documents[i] for i in best]],
                "metadatas": [[self.metadatas[i] for i in best]],
                "distances": [sorted(distances)[:n_results]]}


def new_collection():
    """An empty collection that measures cosine distance (ChromaDB, or numpy when it is missing).
    The index lives in memory; chromadb.PersistentClient(path="index") would save it to disk."""
    if chromadb is None:
        print("chromadb is not installed: using plain numpy search instead (same results)")
        return NumpyCollection()
    client = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False))
    try:
        client.delete_collection("docs")  # start empty, also when we rebuild
    except Exception:
        pass
    # embedding_function=None: we give Chroma our own vectors (from embed())
    return client.create_collection("docs", metadata={"hnsw:space": "cosine"}, embedding_function=None)


def build_index(chunks):
    """Embed every chunk and store it in a vector database (ChromaDB, or the numpy fallback).

    chunks: the list from make_chunks().
    Returns: a dict with exactly these keys (get_index() and search_docs() rely on them):
        {"collection": <the collection>, "chunks": chunks, "vectors": <the embed() array>,
         "settings": _settings()}
    """
    # 1. vectors = embed([chunk["text"] for chunk in chunks])
    # 2. collection = new_collection()   (given above: ChromaDB, or NumpyCollection when chromadb is missing)
    # 3. Call collection.add ONCE with four keyword arguments, all lists in the same order as chunks:
    #      ids=[chunk["id"] ...], embeddings=vectors.tolist(), documents=[chunk["text"] ...],
    #      metadatas=[{"source": chunk["source"], "chunk": chunk["chunk"]} ...]
    # 4. Print f"Indexed {len(chunks)} chunks (CHUNK_SIZE={config.CHUNK_SIZE} words, "
    #          f"CHUNK_OVERLAP={config.CHUNK_OVERLAP}, CHUNK_BY_SECTION={config.CHUNK_BY_SECTION})"
    # 5. Return the dict above.
    raise NotImplementedError("write build_index()")


def search_docs(query, k=None, index=None):
    """Find the k chunks closest in meaning to the query, best first.

    k: how many (None = config.TOP_K). index: the dict from build_index() (None = get_index()).
    Returns: a list of dicts with exactly these keys, highest score first:
        [{"id": "x.txt#3", "text": "...", "source": "x.txt", "chunk": 3, "score": 0.68}, ...]
    "score" is a Python float, 1 - distance (higher = closer in meaning). "chunk" is an int.
    """
    # 1. Fill in k and index. If index["settings"] != _settings(), print a warning that the settings
    #    changed since build_index() (do not rebuild here).
    # 2. found = index["collection"].query(query_embeddings=embed([query]).tolist(),
    #                                      n_results=min(k, index["collection"].count()))
    #    found["ids"][0], found["documents"][0], found["metadatas"][0], found["distances"][0] are lists,
    #    in the same order, best first.
    # 3. For each (chunk_id, text, meta, distance): append {"id": chunk_id, "text": text,
    #    "source": meta["source"], "chunk": int(meta["chunk"]), "score": 1 - float(distance)}.
    # 4. Return the list.
    raise NotImplementedError("write search_docs()")


# ---------------------------------------------------------------- The fix: chunk by section
HEADING = re.compile(r"^\s*(?:#{1,6}\s+(.+?)|=+\s*(.+?)\s*=+)\s*$")  # "## Refunds" or "== Refunds =="


def split_sections(text):
    """Split a text at its headings (lines that match HEADING, e.g. "## Refunds" or "== Refunds ==").

    Returns: a list of (heading, body) tuples in order. heading is the heading text without the "#" or "="
    marks, stripped; text before the first heading gets heading None. Sections whose body is empty or only
    whitespace are left out.
        split_sections("intro\n## A\nfirst\n## B\nsecond") -> [(None, "intro"), ("A", "first"), ("B", "second")]
    """
    # 1. Walk the lines (text.splitlines()), keeping the current heading (start: None) and its lines.
    # 2. When a line matches HEADING: save (current heading, "\n".join(lines)) and start a new section with
    #    heading = (match.group(1) or match.group(2)).strip(). The heading line itself is not part of a body.
    # 3. After the loop, save the last section.
    # 4. Return only the sections whose body.strip() is not empty.
    raise NotImplementedError("write split_sections()")


def chunk_by_section(doc):
    """One chunk per section, each starting with its address (label), for CHUNK_BY_SECTION = True.

    doc: one dict from load_documents().
    Returns: a list of str (NOT dicts: make_chunks() adds the id, source and chunk number), e.g.
        ["01-05 attendance and withdrawal > Unexcused absences over 20% give a DN grade: If the number ...", ...]
    """
    # 1. title = Path(doc["source"]).stem.replace("_", " ").capitalize()
    #      "01-05_Attendance_And_Withdrawal.md" -> "01-05 attendance and withdrawal"
    # 2. For each (heading, body) in split_sections(doc["text"]):
    #      label = f"{title} > {heading}" if heading else title
    #      cut the body with chunk_text(body) (a section longer than CHUNK_SIZE words gives several pieces)
    #      and add f"{label}: {piece}" for every piece, so every piece keeps its label.
    # 3. Return the list of strings.
    raise NotImplementedError("write chunk_by_section()")


# ---------------------------------------------------------------- one shared index
def _settings():
    return (config.CHUNK_SIZE, config.CHUNK_OVERLAP, config.CHUNK_BY_SECTION,
            config.EMBEDDING_MODEL, str(config.CORPUS_DIR))


def build_store(documents=None):
    """Load, chunk, embed and index the whole corpus in one call."""
    documents = load_documents() if documents is None else documents
    return build_index(make_chunks(documents))


def get_index(rebuild=False):
    """The index of the corpus in config.py: built the first time, then reused.
    It is rebuilt automatically when you change CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_BY_SECTION,
    EMBEDDING_MODEL or CORPUS_DIR, and when you ask for it with rebuild=True."""
    global _index
    if rebuild or _index is None or _index["settings"] != _settings():
        _index = build_store()
    return _index


# Names the harness (tools.py, agent.py), the chat server and Session 5 use.
get_store = get_index


def search(store, query, k=None):
    """search_docs() on a given index."""
    return search_docs(query, k, index=store)
