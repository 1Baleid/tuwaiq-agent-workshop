"""
rag.py - Session 3: from documents to a searchable index. Fill in the short TODOs.

    documents  ->  chunks  ->  embeddings  ->  index  ->  search_docs()

  Lab 1  load_documents()    read every .md / .txt file (TODO 1-2)
  Lab 2  chunk_text()        cut a text into pieces of words that overlap (TODO 3-4)
  Lab 3  embed()             turn text into meaning-vectors; compare with keyword_search()
  Lab 4  numpy_search()      search by hand (TODO 5), then build_index() with ChromaDB (TODO 6)
         search_docs()       find the closest chunks, distance -> score (TODO 7)
  Fix    chunk_by_section()  one chunk per section, labelled with its heading (TODO 8)

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
    """The text of one file, or None if we cannot read this kind of file (yet)."""
    path = Path(path)
    if path.suffix.lower() in (".md", ".txt"):
        with open(path, encoding="utf-8") as f:
            # TODO 1: read the whole file and return its text.
            raise NotImplementedError("TODO 1: read the whole file and return its text")
    if path.suffix.lower() == ".pdf":  # PDFs need a library to read them: given
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return None


def load_documents(folder=None):
    """Read every document in the folder (default: config.CORPUS_DIR, e.g. data/kfupm_raw).
    Each document becomes {"source": "01-05_Attendance_And_Withdrawal.pdf", "text": "Article Nine: a student must attend ..."}."""
    folder = Path(folder or config.CORPUS_DIR)
    docs, skipped = [], []
    for path in sorted(glob.glob(str(folder / "*"))):
        text = read_file(path)
        if text is None:
            skipped.append(os.path.basename(path))
            continue
        # TODO 2: add {"source": the file name (os.path.basename(path)), "text": text} to docs.
    print(f"Loaded {len(docs)} documents from {folder}")
    for doc in docs:
        print(f"  {doc['source']}: {len(doc['text'].split())} words")
    if skipped:
        print(f"Skipped {len(skipped)} file(s) this loader cannot read: {', '.join(skipped)}")
    return docs


# ---------------------------------------------------------------- Lab 2: chunk
def chunk_text(text, chunk_size=None, overlap=None):
    """Cut text into chunks of `chunk_size` words. Neighbouring chunks share `overlap` words,
    so a sentence cut at a border is still whole in one of them.

    chunk_text("one two three four five six seven eight nine ten", 4, 1)
    -> ['one two three four', 'four five six seven', 'seven eight nine ten']"""
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    words = text.split()
    # TODO 3: step = how many words each chunk starts after the previous one (chunk_size and overlap).
    raise NotImplementedError("TODO 3-4: set step, then slice chunk_words")
    chunks = []
    for start in range(0, len(words), step):
        # TODO 4: chunk_words = the chunk_size words that begin at `start`.
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):  # this chunk reached the end of the text
            break
    return chunks


def make_chunks(documents):
    """Chunk every document. Each chunk remembers where it came from:
    {"id": "01-05_Attendance_And_Withdrawal.pdf#0", "source": "01-05_Attendance_And_Withdrawal.pdf", "chunk": 0, "text": "..."}"""
    # PLAY WITH THE CHUNKING: change these in config.py, then search again (the index rebuilds by itself).
    #   CHUNK_BY_SECTION  False = a word window that ignores the document's structure (chunk_text)
    #                     True  = one chunk per "## heading" section, with the heading in front (chunk_by_section)
    #   CHUNK_SIZE        words per window. With CHUNK_BY_SECTION = True, a section longer than this is cut
    #                     into pieces. In data/kfupm_structured, 240 of 253 sections fit in 120 words and the
    #                     longest has 167, so CHUNK_SIZE = 170 keeps every rule whole in one chunk.
    #   CHUNK_OVERLAP     words two neighbouring windows share, so a sentence cut at a border survives.
    #   CORPUS_DIR        data/kfupm_structured (sections) or data/kfupm_raw (one plain dump of the same text).
    # Try: raw + word windows, structured + word windows, structured + sections; then CHUNK_SIZE 30 vs 300.
    # Compare which chunk search_docs() puts first for the same question.
    chunks = []
    for doc in documents:
        pieces = chunk_by_section(doc) if config.CHUNK_BY_SECTION else chunk_text(doc["text"])
        for number, text in enumerate(pieces):
            chunks.append({"id": f"{doc['source']}#{number}", "source": doc["source"],
                           "chunk": number, "text": text})
    return chunks


# ---------------------------------------------------------------- Lab 3: embed
def embed(texts):
    """Turn texts into meaning-vectors, one row per text (384 numbers each for all-MiniLM-L6-v2).
    Texts with similar meaning get nearby vectors. The first call downloads the model (about 90 MB)."""
    name = config.EMBEDDING_MODEL
    if name not in _embedders:
        from huggingface_hub.utils import logging as hf_logging
        from sentence_transformers import SentenceTransformer
        hf_logging.set_verbosity_error()  # hides a harmless "Please set a HF_TOKEN" warning (no key is needed)
        _embedders[name] = SentenceTransformer(name)
    # normalize: every vector gets length 1, so "dot product" = cosine similarity (1 = same meaning)
    vectors = _embedders[name].encode(texts, normalize_embeddings=True)
    return np.asarray(vectors, dtype="float32")


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
    `vectors` = embed([chunk["text"] for chunk in chunks])."""
    query_vector = embed([query])[0]
    # TODO 5: scores = one similarity per chunk, in ONE numpy line (dot product of vectors and query_vector).
    raise NotImplementedError("TODO 5: one numpy line for the scores")
    best = np.argsort(-scores)[:k]  # positions of the k highest scores
    return [{**chunks[i], "score": float(scores[i])} for i in best]


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
    """Embed every chunk and store it in a vector database. Returns the index search_docs() needs."""
    vectors = embed([chunk["text"] for chunk in chunks])
    collection = new_collection()
    # TODO 6: fill in embeddings (vectors.tolist()) and metadatas ({"source": ..., "chunk": ...} per chunk).
    raise NotImplementedError("TODO 6: give Chroma the embeddings and the sources")
    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        embeddings=...,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=...,
    )
    print(f"Indexed {len(chunks)} chunks (CHUNK_SIZE={config.CHUNK_SIZE} words, "
          f"CHUNK_OVERLAP={config.CHUNK_OVERLAP}, CHUNK_BY_SECTION={config.CHUNK_BY_SECTION})")
    return {"collection": collection, "chunks": chunks, "vectors": vectors, "settings": _settings()}


def search_docs(query, k=None, index=None):
    """Find the k chunks closest in meaning to the query, best first.
    Returns [{"text", "source", "chunk", "score", "id"}, ...]; higher score = closer in meaning."""
    k = k or config.TOP_K
    index = index or get_index()
    if index["settings"] != _settings():
        print("Warning: chunk/model/corpus settings changed since build_index(). Build the index again.")
    found = index["collection"].query(query_embeddings=embed([query]).tolist(),
                                      n_results=min(k, index["collection"].count()))
    results = []
    for chunk_id, text, meta, distance in zip(found["ids"][0], found["documents"][0],
                                              found["metadatas"][0], found["distances"][0]):
        # TODO 7: add {"id", "text", "source", "chunk", "score"} to results. Chroma gives a distance:
        #         score = 1 - distance (higher = closer in meaning). source and chunk are in meta.
        raise NotImplementedError("TODO 7: build each result; score = 1 - distance")
    return results


# ---------------------------------------------------------------- The fix: chunk by section
HEADING = re.compile(r"^\s*(?:#{1,6}\s+(.+?)|=+\s*(.+?)\s*=+)\s*$")  # "## Refunds" or "== Refunds =="


def split_sections(text):
    """Split a text at its headings: [(heading, body), ...]. Text before the first heading has heading None."""
    sections, heading, lines = [], None, []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            sections.append((heading, "\n".join(lines)))
            heading, lines = (match.group(1) or match.group(2)).strip(), []
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines)))
    return [(heading, body) for heading, body in sections if body.strip()]


def chunk_by_section(doc):
    """One chunk per section, each starting with its address, e.g. "01-05 attendance and withdrawal > Article nine: ...".
    A section longer than CHUNK_SIZE words is cut with chunk_text(), and every piece keeps the label."""
    title = Path(doc["source"]).stem.replace("_", " ").capitalize()  # "01-05_Attendance_And_Withdrawal.pdf" -> "01-05 attendance and withdrawal"
    chunks = []
    for heading, body in split_sections(doc["text"]):
        label = f"{title} > {heading}" if heading else title
        for piece in chunk_text(body):
            # TODO 8: add the piece to chunks with its label in front: "<label>: <piece>".
            raise NotImplementedError("TODO 8: put the label in front of each piece")
    return chunks


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
