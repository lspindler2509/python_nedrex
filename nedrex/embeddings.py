"""Semantic search over the collections embedded by a NeDRex instance."""

from typing import Any as _Any
from typing import Optional as _Optional

from nedrex._common import request as _request
from nedrex.exceptions import NeDRexError


def get_available() -> _Any:
    """Return available embedding indexes and collections from /embeddings/available."""
    return _request("/embeddings/available")


def query(query: str, collection: _Optional[str] = None, top: int = 10) -> _Any:
    """Search embedded collections by text, returning at most top semantic matches.

    collection=None searches across embedded collections. This is a top-k search,
    not a paginated collection scan. Scores are similarity, not biomedical evidence.
    """
    if isinstance(top, bool) or not isinstance(top, int) or top <= 0:
        raise ValueError("top must be a positive integer")
    if collection is not None:
        available = get_available()
        if collection not in available:
            # Collection names are case-sensitive; the server answers unknown names with 404.
            raise NeDRexError(f"collection {collection!r} is not embedded; choose one of: {', '.join(available)}")
    return _request("/embeddings/query", "post", json={"query": query, "collection": collection, "top": top})
