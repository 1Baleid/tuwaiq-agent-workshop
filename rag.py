"""
rag.py - Session 1: from documents to a searchable index.

    documents  ->  chunks  ->  embeddings (vectors)  ->  index  ->  search

    import rag
    store = rag.build_store()            # load, chunk, embed and index the corpus
    for hit in rag.search(store, "How many hours is one credit?"):
        print(round(hit["score"], 2), hit["id"], hit["text"][:80])

Later sessions call rag.get_store(), which builds the store once and reuses it.
"""
import numpy as np

import config

try:
    import faiss  # FAISS: a fast library for searching vectors
except ImportError:  # no faiss for this computer (e.g. an older Mac): plain numpy below does the same job
    faiss = None

_embedders = {}  # embedding models we already loaded, by name
_store = None    # the store get_store() built last


# ---------------------------------------------------------------- 1. load
def read_file(path):
    """The text of one document, or None if we cannot read this kind of file."""
    if path.suffix.lower() in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return None


def load_documents(corpus_dir=None):
    """Read every document in <corpus>/docs that read_file() understands (.txt, .md, .pdf).
    Returns a list of {"source": file name, "text": the whole text}."""
    folder = (corpus_dir or config.CORPUS_DIR) / "docs"
    documents, skipped = [], []
    for path in sorted(folder.iterdir()):
        text = read_file(path)
        if text is None:
            skipped.append(path.name)
        else:
            documents.append({"source": path.name, "text": text})
    print(f"Loaded {len(documents)} documents from {folder}")
    if skipped:
        print(f"Skipped {len(skipped)} file(s) this loader cannot read: {', '.join(skipped)}")
    return documents


# ---------------------------------------------------------------- 2. chunk
def chunk_text(text, size=None, overlap=None):
    """Cut text into pieces of `size` characters. Each piece starts `overlap` characters
    before the previous one ended, so a sentence cut at a border is still whole somewhere."""
    size = size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
    if overlap >= size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    # SOLUTION START: TODO (Session 1): cut `text` into chunks of `size` characters that overlap by `overlap`
    chunks = []
    start = 0
    while True:
        chunks.append(text[start:start + size].strip())
        if start + size >= len(text):
            break
        start += size - overlap
    return [chunk for chunk in chunks if chunk]
    # SOLUTION END


def make_chunks(documents):
    """Chunk every document. Each chunk remembers where it came from, e.g. id 'course_credit.txt#3'."""
    chunks = []
    for doc in documents:
        for number, text in enumerate(chunk_text(doc["text"]), start=1):
            chunks.append({"id": f"{doc['source']}#{number}", "source": doc["source"], "text": text})
    return chunks


# ---------------------------------------------------------------- 3. embed
def embed(texts):
    """Turn texts into vectors, one row per text. Texts with similar meaning get similar vectors.
    The first call downloads the embedding model (about 90 MB)."""
    name = config.EMBEDDING_MODEL
    if name not in _embedders:
        from huggingface_hub.utils import logging as hf_logging
        from sentence_transformers import SentenceTransformer
        hf_logging.set_verbosity_error()  # hides a harmless "Please set a HF_TOKEN" warning (no key is needed)
        _embedders[name] = SentenceTransformer(name)
    # normalize: every vector gets length 1, so "dot product" = cosine similarity (1 = same meaning)
    vectors = _embedders[name].encode(texts, normalize_embeddings=True)
    return np.asarray(vectors, dtype="float32")


# ---------------------------------------------------------------- 4. index
class NumpyIndex:
    """The same job as faiss.IndexFlatIP, in plain numpy. Used only when faiss is missing."""

    def __init__(self, vectors):
        self.vectors = vectors

    def search(self, queries, k):
        scores = queries @ self.vectors.T                    # similarity to every chunk
        rows = np.argsort(-scores, axis=1)[:, :k]           # positions of the k best
        return np.take_along_axis(scores, rows, axis=1), rows


def build_store(documents=None):
    """Load, chunk, embed and index the corpus. Returns the 'store' that search() needs."""
    documents = load_documents() if documents is None else documents
    chunks = make_chunks(documents)
    vectors = embed([chunk["text"] for chunk in chunks])
    if faiss is not None:
        index = faiss.IndexFlatIP(vectors.shape[1])  # IP = inner product (cosine for normalized vectors)
        index.add(vectors)
    else:
        print("faiss is not installed: using plain numpy search instead (same results)")
        index = NumpyIndex(vectors)
    print(f"Indexed {len(chunks)} chunks (CHUNK_SIZE={config.CHUNK_SIZE}, CHUNK_OVERLAP={config.CHUNK_OVERLAP})")
    return {"index": index, "chunks": chunks, "settings": _settings()}


def _settings():
    return config.CHUNK_SIZE, config.CHUNK_OVERLAP, config.EMBEDDING_MODEL, str(config.CORPUS_DIR)


def get_store(rebuild=False):
    """The store for the corpus in config.py: built the first time, then reused.
    It is rebuilt automatically if you change CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL or CORPUS_DIR,
    and when you ask for it with rebuild=True (e.g. after changing the documents)."""
    global _store
    if rebuild or _store is None or _store["settings"] != _settings():
        _store = build_store()
    return _store


# ---------------------------------------------------------------- 5. search
def search(store, query, k=None):
    """Return the k chunks most similar to the query, best first.
    Each result is a chunk plus its "score" (higher = closer in meaning)."""
    k = k or config.TOP_K
    if store["settings"] != _settings():
        print("Warning: chunk/model/corpus settings changed since build_store(). Run build_store() again.")
    # SOLUTION START: TODO (Session 1): embed the query, ask store["index"] for the k best rows, return those chunks with their scores
    scores, rows = store["index"].search(embed([query]), k)
    results = []
    for score, row in zip(scores[0], rows[0]):
        if row == -1:  # FAISS fills with -1 when there are fewer than k chunks
            continue
        results.append({**store["chunks"][row], "score": float(score)})
    return results
    # SOLUTION END
