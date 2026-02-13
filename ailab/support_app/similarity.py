from __future__ import annotations

from dataclasses import dataclass

from langchain_community.vectorstores import FAISS

from .llm import get_embeddings
from .types import SimilarityHit


@dataclass
class SimilarityIndex:
    vectorstore: FAISS

    @classmethod
    def from_closed_tickets(cls, tickets: list[dict]) -> "SimilarityIndex":
        texts: list[str] = []
        metadatas: list[dict] = []
        for t in tickets:
            issue = (t.get("issue_description") or "").strip()
            solution = (t.get("solution") or "").strip()
            if not issue or not solution:
                continue
            texts.append(issue)
            metadatas.append(
                {
                    "ticket_id": str(t.get("ticket_id")),
                    "user_id": str(t.get("user_id")),
                    "issue_description": issue,
                    "solution": solution,
                }
            )

        embeddings = get_embeddings()
        if not texts:
            empty = FAISS.from_texts(["__empty__"], embeddings, metadatas=[{"empty": True}])
            return cls(vectorstore=empty)
        vs = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        return cls(vectorstore=vs)

    def search(self, query: str, k: int = 5) -> list[SimilarityHit]:
        q = (query or "").strip()
        if not q:
            return []
        docs_and_scores = self.vectorstore.similarity_search_with_score(q, k=k)
        hits: list[SimilarityHit] = []
        for doc, score in docs_and_scores:
            md = doc.metadata or {}
            if md.get("empty"):
                continue
            hits.append(
                {
                    "ticket_id": md.get("ticket_id", ""),
                    "user_id": md.get("user_id", ""),
                    "issue_description": md.get("issue_description", ""),
                    "solution": md.get("solution", ""),
                    "score": float(score),
                }
            )
        hits.sort(key=lambda x: x["score"])
        return hits
