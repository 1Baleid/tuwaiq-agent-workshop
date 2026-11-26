"""
chat_server.py - a web chat for asking questions about KFUPM documents.

    python chat_server.py            then open http://localhost:8000

The page (a React app in frontend/, built into frontend/dist) sends each question to POST /api/chat. The server passes it to
agent.run_agent(), which searches the documents (rag.py) and asks the LLM (llm.py) for an
answer with [source] citations. Only the Python standard library is used, so nothing new to install.
"""
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agent
import config
import rag

DIST = config.ROOT / "frontend" / "dist"  # the built React app
PORT = int(os.environ.get("PORT", "8000"))
_lock = threading.Lock()  # one question at a time: the store and free LLM tiers are not built for parallel calls


class ChatHandler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status, payload):
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"ok": True, "chunks": len(rag.get_store()["chunks"]),
                                  "corpus": config.CORPUS_DIR.name, "provider": config.LLM_PROVIDER})
        else:
            self._send_static()

    def _send_static(self):
        """Serve the built React app from frontend/dist (run `npm run build` in frontend/ first)."""
        path = self.path.split("?")[0].lstrip("/") or "index.html"
        file = (DIST / path).resolve()
        if not file.is_relative_to(DIST.resolve()) or not file.is_file():
            file = DIST / "index.html"  # unknown paths get the app itself
        if not file.is_file():
            return self._send(500, "React app not built: run `npm install` and `npm run build` in frontend/",
                              "text/plain; charset=utf-8")
        data = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/chat":
            return self._send_json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            question = str(body.get("question", "")).strip()
            history = body.get("history") or []
        except (ValueError, TypeError):
            return self._send_json(400, {"error": "bad JSON"})
        if not question:
            return self._send_json(400, {"error": "empty question"})

        with _lock:
            try:
                result = agent.run_agent(question, history=history)
            except Exception as e:  # e.g. missing API key: show it in the chat instead of crashing
                return self._send_json(500, {"error": f"{type(e).__name__}: {e}"})

        # Send back the text of each cited chunk too, so the page can show where the answer came from.
        chunks = {chunk["id"]: chunk for chunk in rag.get_store()["chunks"]}
        sources = [{"id": cid, "text": chunks[cid]["text"]} for cid in result["sources"] if cid in chunks]
        self._send_json(200, {"answer": result["answer"], "sources": sources, "history": result["history"],
                              "seconds": result["seconds"], "tools": result["tools_used"]})

    def log_message(self, fmt, *args):  # quieter console: only errors
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    print(f"Building the index for {config.CORPUS_DIR} (first run downloads the embedding model) ...")
    rag.get_store()
    print(f"KFUPM chat ready: http://localhost:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), ChatHandler).serve_forever()
