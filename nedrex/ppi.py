# -*- coding: utf-8 -*-
"""Module containing a function to access PPI routes in a NeDRex instance
"""
from typing import Any as _Any
from typing import Dict as _Dict
from typing import Generator as _Generator
from typing import Iterable as _Iterable
from typing import List as _List
from typing import Optional as _Optional

from nedrex import config as _config
from nedrex._common import check_pagination_limit as _check_pagination_limit
from nedrex._common import check_response as _check_response
from nedrex._common import get_pagination_limit as _get_pagination_limit
from nedrex._common import http as _http
from nedrex._common import iter_pages as _iter_pages
from nedrex.exceptions import NeDRexError


def ppis(
    evidence: _Iterable[str],
    skip: int = 0,
    limit: _Optional[int] = None,
    reviewed_proteins: _Optional[_Iterable[bool]] = [True, False],
    skip_proteins: _Optional[int] = 0,
    limit_proteins: _Optional[int] = 250000,
    nodes: _Optional[_List[str]] = None,
    sources: _Optional[_List[str]] = None,
    num_sources: _Optional[int] = None,
    hippie_methods_score_cutoff: _Optional[float] = None,
    methods_score_cutoff: _Optional[float] = None,
) -> _List[_Dict[str, _Any]]:
    """Obtain PPIs from a NeDRex instance

    Parameters
    ----------
    evidence : iterable[str]
        A list of evidence types with which to filter PPIs. Valid values
        are "exp" (experimental), "pred" (predicted), and "ortho"
        (orthologous).
    skip : int, optional
        The number of records to skip before returning PPIs. The default
        value is 0 (skip no records).
    limit : int, optional
        The number of records to return. The default value, None, uses the
        maximum pagination limit for the NeDRex instance being queried.
    reviewed_proteins: iterable[bool], optional
       Protein reviewed state according to UniProt for proteins to be included in the returned PPIs.
    skip_proteins: int, optional
        The number of proteins to skip before returning PPIs. The default value is 0 (skip no records).
    limit_proteins: int, optional
        The number of proteins to return, in order of precedence. The default value is 250000 (all proteins).
    nodes : list[str], optional
        Native node filter; some deployed servers advertise but ignore this field.
    sources : list[str], optional
        Source database names.
    num_sources : int, optional
        Minimum number of supporting sources.
    hippie_methods_score_cutoff : float, optional
        Methods-score filter on api.nedrex.net.
    methods_score_cutoff : float, optional
        Corresponding filter on the TUM instance.

    Returns
    -------
    list[dict[str, Any]]
        A list of PPI edges returned from the NeDRexAPI.
    """
    evidence_set = set(evidence)
    extra_evidence = evidence_set - {"exp", "pred", "ortho"}
    if extra_evidence:
        raise NeDRexError(f"unexpected evidence types: {extra_evidence}")

    maximum_limit = _get_pagination_limit()
    _check_pagination_limit(limit, maximum_limit)

    body = {
        "iid_evidence": list(evidence_set),
        "skip": skip,
        "limit": limit,
        "reviewed_proteins": reviewed_proteins,
        "skip_proteins": skip_proteins,
        "limit_proteins": limit_proteins,
    }
    body.update(
        {
            k: v
            for k, v in {
                "nodes": nodes,
                "sources": sources,
                "num_sources": num_sources,
                "hippie_methods_score_cutoff": hippie_methods_score_cutoff,
                "methods_score_cutoff": methods_score_cutoff,
            }.items()
            if v is not None
        }
    )
    resp = _http.post(f"{_config.url_base}/ppi", json=body, headers={"x-api-key": _config.api_key})
    result: _List[_Dict[str, _Any]] = _check_response(resp)
    return result


def iter_ppis(
    evidence: _Iterable[str] = ("exp",),
    reviewed_proteins: _Optional[_Iterable[bool]] = None,
    skip_proteins: _Optional[int] = 0,
    limit_proteins: _Optional[int] = 250000,
    nodes: _Optional[_List[str]] = None,
    sources: _Optional[_List[str]] = None,
    num_sources: _Optional[int] = None,
    hippie_methods_score_cutoff: _Optional[float] = None,
    methods_score_cutoff: _Optional[float] = None,
    page_size: _Optional[int] = None,
    skip: int = 0,
    max_records: _Optional[int] = None,
) -> _Generator[_Dict[str, _Any], None, None]:
    """Yield PPI pages with all filters preserved; optionally stop after max_records.

    page_size limits each PPI request; skip is the initial PPI offset. The protein
    window stays fixed across pages. Filters have the same meaning as in ppis.
    """
    evidence = list(evidence)
    reviewed = [True, False] if reviewed_proteins is None else list(reviewed_proteins)
    yield from _iter_pages(
        lambda offset, limit: ppis(
            evidence,
            offset,
            limit,
            reviewed,
            skip_proteins,
            limit_proteins,
            nodes,
            sources,
            num_sources,
            hippie_methods_score_cutoff,
            methods_score_cutoff,
        ),
        page_size,
        skip,
        max_records,
    )


def ppi_network(
    evidence: _Iterable[str] = ("exp",),
    reviewed_proteins: _Optional[_Iterable[bool]] = None,
    skip_proteins: _Optional[int] = 0,
    limit_proteins: _Optional[int] = 250000,
    nodes: _Optional[_List[str]] = None,
    sources: _Optional[_List[str]] = None,
    num_sources: _Optional[int] = None,
    hippie_methods_score_cutoff: _Optional[float] = None,
    methods_score_cutoff: _Optional[float] = None,
    page_size: _Optional[int] = None,
    skip: int = 0,
    max_records: _Optional[int] = None,
    compact: bool = False,
) -> _Any:
    """Download all matching PPIs as an undirected edge list of UniProt accessions.

    Pages through the PPIs like iter_ppis, with the same filters, but keeps only the
    interacting proteins: the "uniprot." prefix is removed, self-loops are dropped and
    each pair appears once regardless of direction. Pages are processed one at a time,
    so the full PPI records are not kept in memory.

    Parameters
    ----------
    compact : bool, optional
        If False (default), returns [{"from": ..., "to": ...}, ...]. If True, returns
        {"nodes": [...], "edges": [[i, j], ...]} with positions in "nodes", about a
        third of the size for large networks.

    Other parameters have the same meaning as in ppis and iter_ppis; skip and
    max_records count downloaded PPI records, not the returned edges. A protein
    window (skip_proteins, limit_proteins) only returns edges with both proteins
    inside it, so the network then lacks the edges between windows.

    Returns
    -------
    list[dict[str, str]] or dict[str, list]
        Edges sorted by accession.
    """

    def accession(member: str) -> str:
        return member[len("uniprot.") :] if member.startswith("uniprot.") else member

    pairs = set()
    for record in iter_ppis(
        evidence,
        reviewed_proteins,
        skip_proteins=skip_proteins,
        limit_proteins=limit_proteins,
        nodes=nodes,
        sources=sources,
        num_sources=num_sources,
        hippie_methods_score_cutoff=hippie_methods_score_cutoff,
        methods_score_cutoff=methods_score_cutoff,
        page_size=page_size,
        skip=skip,
        max_records=max_records,
    ):
        a, b = accession(record["memberOne"]), accession(record["memberTwo"])
        if a != b:
            pairs.add((a, b) if a < b else (b, a))
    edges = sorted(pairs)
    if not compact:
        return [{"from": a, "to": b} for a, b in edges]
    positions: _Dict[str, int] = {}
    indexed = [[positions.setdefault(a, len(positions)), positions.setdefault(b, len(positions))] for a, b in edges]
    return {"nodes": list(positions), "edges": indexed}
