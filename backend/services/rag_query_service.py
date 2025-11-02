"""RAG query utilities for orchestrator-mediated knowledge retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from backend.prompts.orchestrator_prompts import RAGPattern


@dataclass(frozen=True)
class RAGSearchResult:
    """Internal representation of a raw RAG search response."""

    title: str
    problem: str
    solution: str
    when_to_try: str
    success_count: int
    similarity: float


class RAGQueryService:
    """Orchestrator-only entry point for retrieving RAG knowledge (Decision 68)."""

    def __init__(self, *, client: Optional[Any] = None, collection: str = "project_knowledge") -> None:
        self._client = client
        self._collection = collection

    async def search(
        self,
        *,
        query: str,
        agent_type: str,
        task_type: str,
        technology: Optional[str] = None,
        limit: int = 5,
    ) -> List[RAGPattern]:
        """Search the knowledge base and return normalized RAG patterns."""

        if not self._client or not hasattr(self._client, "search"):
            return []

        filter_payload = {
            "agent_type": agent_type,
            "task_type": task_type,
        }
        if technology:
            filter_payload["technology"] = technology

        raw_results = await self._client.search(  # type: ignore[no-any-unimported]
            collection_name=self._collection,
            query_text=query,
            filters=filter_payload,
            limit=limit,
        )

        patterns: List[RAGPattern] = []
        for item in _ensure_iterable(raw_results):
            payload = getattr(item, "payload", None) or item.get("payload", {})
            patterns.append(
                RAGPattern(
                    title=payload.get("title", "Historical pattern"),
                    success_count=payload.get("success_count", 0),
                    problem=payload.get("problem", ""),
                    solution=payload.get("solution", ""),
                    when_to_try=payload.get("when_to_try", ""),
                    similarity=float(getattr(item, "score", item.get("score", 0.0))),
                )
            )

        return patterns[:limit]


def _ensure_iterable(results: Any) -> Iterable[Any]:
    if results is None:
        return []
    if isinstance(results, Iterable) and not isinstance(results, (str, bytes, dict)):
        return results
    return [results]
