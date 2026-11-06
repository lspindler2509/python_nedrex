"""Identifier translation routes (available on api.nedrex.net, instance dependent)."""

from typing import Any as _Any
from typing import List as _List

from nedrex._common import request as _request


def translate_entrez(nodes: _List[str]) -> _Any:
    """Translate gene symbols, Ensembl IDs or UniProt accessions to Entrez IDs.

    Returns a dict keyed by the input; values are lists of unprefixed Entrez IDs
    (e.g. {"EGFR": ["1956"]}). Unknown inputs map to empty lists.
    """
    return _request("/translate/translate_entrez", "post", json={"nodes": nodes})


def translate_uniprot(nodes: _List[str]) -> _Any:
    """Translate gene symbols or Entrez IDs to UniProt accessions.

    Returns a dict keyed by the input; values may contain several accessions
    (reviewed and unreviewed entries). Inputs without a namespace prefix that are
    already UniProt accessions are returned unchanged.
    """
    return _request("/translate/translate_uniprot", "post", json={"nodes": nodes})
