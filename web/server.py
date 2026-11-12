#!/usr/bin/env python3
"""RAGSieve interactive demo server.

Zero-dependency static server (Python standard library only). It merges the
pre-computed demo outputs into a single JSON payload for the browser, so the
frontend never has to parse JSONL or know the on-disk layout.

Run from the repository root:

    uv run python web/server.py

Then open http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent
INDEX = WEB / "index.html"

# How many ranked documents to expose per retrieval context. RSQ scores the
# top-5 against ranks 6-20, so 20 is the natural inspection window.
CONTEXT_WINDOW = 20


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_condition(query_id: str, ctx: dict, rsq_by_key: dict, filtered_by_key: dict) -> dict:
    condition = ctx["condition"]
    docs: list[dict] = []
    for doc in ctx["documents"][:CONTEXT_WINDOW]:
        document_id = doc["id"]
        prediction = rsq_by_key.get((query_id, condition, document_id))
        docs.append(
            {
                "rank": doc["rank"],
                "document_id": document_id,
                "text": doc["text"],
                "poison": bool(doc.get("poison", False)),
                # Full RSQ evidence record when the document is a scored candidate
                # (ranks 1-5); None for the reference tail (ranks 6-20).
                "rsq": prediction,
            }
        )

    filtered = filtered_by_key.get((query_id, condition))
    return {
        "condition": condition,
        "docs": docs,
        "filtered": {
            "retained_ranks": [d["rank"] for d in filtered["documents"]] if filtered else [],
            "removed_ids": filtered.get("removed_document_ids", []) if filtered else [],
            "removed_count": filtered.get("removed_count", 0) if filtered else 0,
        },
    }


def build_data() -> dict:
    contexts = load_jsonl(ROOT / "data" / "demo" / "contexts.jsonl")
    rsq = load_jsonl(ROOT / "outputs" / "demo" / "rsq-predictions.jsonl")
    filtered = load_jsonl(ROOT / "outputs" / "demo" / "filtered-top5.jsonl")
    rsg_pred = load_jsonl(ROOT / "outputs" / "demo" / "rsg-predictions.jsonl")
    labels = load_jsonl(ROOT / "data" / "demo" / "labels.jsonl")
    corpus = load_jsonl(ROOT / "data" / "demo" / "corpus.jsonl")

    rsq_metrics = read_json(ROOT / "outputs" / "demo" / "rsq-metrics.json")
    rsg_metrics = read_json(ROOT / "outputs" / "demo" / "rsg-metrics.json")

    rsq_by_key = {(p["query_id"], p["condition"], p["document_id"]): p for p in rsq}
    filtered_by_key = {(f["query_id"], f["condition"]): f for f in filtered}

    by_query: dict[str, dict[str, dict]] = {}
    for ctx in contexts:
        by_query.setdefault(ctx["query_id"], {})[ctx["condition"]] = ctx

    queries: list[dict] = []
    for query_id, conditions in by_query.items():
        attacked_condition = next(k for k in conditions if k != "clean")
        attacked = conditions[attacked_condition]
        clean = conditions.get("clean", attacked)
        queries.append(
            {
                "query_id": query_id,
                "query": attacked["query"],
                "attack_type": attacked_condition,
                "correct_answers": attacked.get("correct_answers", []),
                "target_answer": attacked.get("target_answer", ""),
                "clean": build_condition(query_id, clean, rsq_by_key, filtered_by_key),
                "attacked": build_condition(query_id, attacked, rsq_by_key, filtered_by_key),
            }
        )

    label_map = {r["document_id"]: bool(r["poison"]) for r in labels}
    text_map = {r["document_id"]: r["text"] for r in corpus}

    rsg_docs: list[dict] = []
    for p in rsg_pred:
        document_id = p["document_id"]
        rsg_docs.append(
            {
                "document_id": document_id,
                "score": p["score"],
                "flagged": bool(p["flagged"]),
                "poison": label_map.get(document_id, False),
            }
        )
    rsg_docs.sort(key=lambda d: d["score"], reverse=True)

    flagged = [d for d in rsg_docs if d["flagged"]]
    for d in flagged:
        d["text"] = text_map.get(d["document_id"], "")

    return {
        "queries": queries,
        "rsg": {
            "docs": rsg_docs,
            "flagged": flagged,
            "metrics": rsg_metrics,
        },
        "metrics": {"rsq": rsq_metrics, "rsg": rsg_metrics},
    }


DATA = build_data()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self._send(200, body, "text/html; charset=utf-8")
        elif self.path == "/api/data":
            body = json.dumps(DATA, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, *args) -> None:  # noqa: D102
        pass  # keep the console quiet


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"RAGSieve demo running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
