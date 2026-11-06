# -*- coding: utf-8 -*-
"""Functions to access the comorbiditome in NeDRex
"""

from pathlib import Path
from typing import Dict as _Dict
from typing import List as _List
from typing import Literal
from typing import Optional as _Optional
from typing import Union as _Union

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import check_status_factory as _check_status_factory
from nedrex._common import download_file as _download_file
from nedrex._common import http as _http

__all__ = [
    "map_icd10_to_mondo",
    "map_mondo_to_icd10",
    "get_icd10_associations",
    "submit_comorbiditome_build",
    "check_comorbiditome_status",
    "download_comorbiditome_build",
]


def map_icd10_to_mondo(disorders: _List[str]) -> _Dict[str, _List[str]]:
    """Map a list of disorders in ICD10 to the MONDO namespace

    In moving between ICD10 and MONDO, the scope of the disorder may change. A
    term in ICD10 may be broader, more specific, or only partially overlap with
    the scope of a MONDO disorder.

    Parameters
    ----------
    disorders : list[str]
        A list of disorders in the ICD-10 namespace.

    Returns
    -------
    dict[str, list[str]]
        A dictionary mapping input ICD-10 codes to MONDO codes.
    """
    url = f"{_config.url_base}/comorbiditome/icd10_to_mondo"

    params = {"icd10": disorders}
    headers = {"x-api-key": _config.api_key}

    response = _http.post(url, json=params, headers=headers)
    result: _Dict[str, _List[str]] = _check_response(response)
    return result


def map_mondo_to_icd10(
    disorders: _List[str], only_3char: bool = False, exclude_3char: bool = False
) -> _Dict[str, _List[str]]:
    """Map a list of disorders in MONDO to the ICD10 namespace

    In moving between MONDO and ICD10, the scope of the disorder may change. A
    term in MONDO may be broader, more specific, or only partially overlap with
    the scope of an ICD10 disorder.

    Parameters
    ----------
    disorders : list[str]
        A list of disorders in the MONDO namespace
    only_3char : bool, optional
        Whether to only include 3-character ICD-10 codes, by default False
    exclude_3char : bool, optional
        Whether to exclude 3-character ICD-10 codes, by default False

    Returns
    -------
    dict[str, list[str]]
        A dictionary mapping input MONDO codes to ICD-10 codes
    """
    url = f"{_config.url_base}/comorbiditome/mondo_to_icd10"

    params = {"mondo": disorders, "only_3char": only_3char, "exclude_3char": exclude_3char}
    headers = {"x-api-key": _config.api_key}

    response = _http.post(url, json=params, headers=headers)
    result: _Dict[str, _List[str]] = _check_response(response)
    return result


_EdgeTypes = Literal[
    "gene_associated_with_disorder",
    "drug_has_indication",
    "drug_has_contraindication",
    "drug_targets_disorder_associated_gene_product",
]


def get_icd10_associations(nodes: _List[str], edge_type: _EdgeTypes) -> _Dict[str, _List[str]]:
    """Get edge types from NeDRex, with disorder IDs mapped to ICD-10

    This function takes as arguments an `edge_type`, which is a string
    specifying the edge type of interest, and a list of nodes. `nodes` should
    contain a list of primary IDs for the nodes of the _non_ disorder type in
    a relationship that you wish to obtain associations for.

    For example, you could select the `gene_associated_with_disorder` edge type
    and pass in the CFTR gene as your disorder of interest, `["entrez.1080"]`.

    Note that one edge type, `drug_targets_disorder_associated_gene_product`,
    is an inferred edge. This follows the path of:

    - `(drug)-[has_target]-(protein)`
    - `(protein)-[encoded_by]-(gene)`
    - `(gene)-[associated_with]-(disorder)`


    Parameters
    ----------
    nodes : list[str]
        A list of node IDs for the non-disorder member of relationships
    edge_type : str
        The edge type you with to obtain relationships for

    Returns
    -------
    dict[str, list[str]]
        A dictionary mapping input nodes to the disorders they have a
        relationship with (in the ICD-10 namespace).
    """
    url = f"{_config.url_base}/comorbiditome/get_icd10_associations"

    params = {"node": nodes, "edge_type": edge_type}
    headers = {"x-api-key": _config.api_key}

    response = _http.get(url, params=params, headers=headers)
    result: _Dict[str, _List[str]] = _check_response(response)
    return result


def submit_comorbiditome_build(
    max_phi_cor: _Optional[float] = None,
    min_phi_cor: _Optional[float] = None,
    max_p_value: _Optional[float] = None,
    min_p_value: _Optional[float] = None,
    mondo: _Optional[list[str]] = None,
) -> str:
    """Submit a comorbiditome build request

    Parameters
    ----------
    max_phi_cor : float | None, optional
        The maximum phi correlation to include an edge in the comorbiditome, by
        default `None` (no maximum)
    min_phi_cor : float | None, optional
        The minimum phi correlation to include an edge in the comorbiditome, by
        default `None` (no minimum)
    max_p_value : float | None, optional
        The maximum p-value to include an edge in the network, by default
        `None` (no maximum)
    min_p_value : float | None, optional
        The minimum p-value to include an edge in the network, by default
        `None` (no minimum)
    mondo : list[str] | None, optional
        MONDO nodes to map to ICD-10 and induce a subnetwork of the
        comorbiditome, by default `None` (no subnetwork induced)

    Returns
    -------
    str
        UID of the submitted comorbiditome job
    """
    url = f"{_config.url_base}/comorbiditome/submit_comorbiditome_build"

    body = {
        "mondo": mondo,
        "max_phi_cor": max_phi_cor,
        "min_phi_cor": min_phi_cor,
        "max_p_value": max_p_value,
        "min_p_value": min_p_value,
    }
    headers = {"x-api-key": _config.api_key}

    response = _http.post(url, json=body, headers=headers)
    result: str = _check_response(response)
    return result


check_comorbiditome_status = _check_status_factory("/comorbiditome/comorbiditome_build_status")
check_comorbiditome_status.__name__ = "check_comorbiditome_status"
check_comorbiditome_status.__doc__ = """Gets details of a submitted comorbiditome build job

    Parameters
    ----------
    uid : str
        The unique ID of a comorbiditome build job

    Returns
    -------
    dict[str, Any]
        Details of the current comorbiditome build job; the status of job
        is stored using the `status` key
"""


_Formats = Literal["tsv", "graphml"]


def download_comorbiditome_build(uid: str, fmt: _Formats, save_path: _Optional[str] = None) -> _Union[str, None]:
    """Download a completed comorbiditome build

    Parameters
    ----------
    uid : str
        The UID of the comorbiditome build job.
    fmt : Formats
        The format to return the comorbiditome in. Should be one of `tsv` or
        `graphml`.
    save_path : str | None, optional
        Where to save the graph. If a string is provided (representing a
        filepath), then the graph is saved to this file. If `None`, then the
        graph is returned as a string. Default is `None`.

    Returns
    -------
    str | None
        If `save_path` is set, then `None` is returned. Otherwise, the graph is
        returned a string.
    """
    if save_path is None:
        filename = "none.txt"
    else:
        filename = Path(save_path).name

    url = f"{_config.url_base}/comorbiditome/download_comorbiditome_build/" f"{uid}/{fmt}/{filename}"

    if save_path:
        _download_file(url, save_path)
        return None

    response = _http.get(url, headers={"x-api-key": _config.api_key})
    result: str = _check_response(response, return_type="text")
    return result
