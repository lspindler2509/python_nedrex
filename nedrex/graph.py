from pathlib import Path as _Path
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Optional as _Optional
from urllib.parse import quote as _quote

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import download_file as _download_file
from nedrex._common import http as _http


# pylint: disable=R0913
def build_request(
    nodes: _Optional[_List[str]] = None,
    edges: _Optional[_List[str]] = None,
    ppi_evidence: _Optional[_List[str]] = None,
    include_ppi_self_loops: bool = False,
    taxid: _Optional[_List[int]] = None,
    drug_groups: _Optional[_List[str]] = None,
    concise: bool = True,
    include_omim: bool = True,
    disgenet_threshold: float = 0.0,
    use_omim_ids: bool = False,
    split_drug_types: bool = False,
    reviewed_proteins: _Optional[_List[bool]] = None,
) -> str:
    """Submit a build request to NeDRex to build a graph

    Parameters
    ----------
    nodes : list[str], optional
        The list of node types to be included in the graph. The default is
        ["disorder", "drug", "gene", "protein"]
    edges : list[str], optional
        The list of edge types to be included in the graph. The default is
        ["disorder_is_subtype_of_disorder", "drug_has_indication",
        "drug_has_target", "protein_encoded_by_gene",
        "protein_interacts_with_protein",]
    ppi_evidence : list[str], optional
        A list of evidence types -- for a PPI edge to be included in the
        graph, it must be asserted with evidence listed in `ppi_evidence`.
        Possible values are `exp` (experimental), `pred` (predicted) and
        `ortho` (orthologous). The default is [`exp`].
    include_ppi_self_loops :  bool, optional
        Whether or not to include self-loops for PPI edges. The default,
        False, does not include PPI self-loops.
    taxid : list[int], optional
        A list of NCBI taxonomy IDs with which to filter proteins in the
        network. The default is [9606,], which includes only Homo sapiens
        proteins. Note that, at the time of writing, NeDRexDB only has
        Homo sapiens proteins.
    drug_groups : list[str], optional
        A list of drug groups with which to filter drugs to be included in
        the graph. The default, ["approved",], only includes drugs that
        have an approved use.
    concise : bool, optional
        Whether or not to return a concise view of the network. The
        default, True, removes some attributes from nodes and edges in the
        network to result in a smaller, more tractable network.
    include_omim : bool, optional
        Whether or not to include gene-disorder associations from OMIM.
        The default, True, includes these gene-disorder associations.
    disgenet_threshold : float, optional
        The threshold at which to include gene-disorder associations from
        DisGeNET. DisGeNET gene-disorder associations are given a score
        in the range [0,1], reflecting factors such as the number of
        sources and the level of curation. Edges with a score ≥ the given
        threshold are kept. The default value is 0.0
    use_omim_ids : bool, optional
        Whether or not to use OMIM IDs on disorder nodes instead of MONDO
        IDs (where possible). The default, False, uses MONDO IDs for all
        disorder nodes.
    reviewed_proteins : list[bool], optional
        Select reviewed/unreviewed UniProt records; None keeps the server default.
    split_drug_types : bool, optional
        Whether or not to split "Drug" nodes into "SmallMoleculeDrug" and
        "BiotechDrug". The default, False, consolidates all drugs into a
        single "Drug" type.

    Returns
    -------
    str
        The unique ID of the graph build job.

    Notes
    -----
    For more information on the DisGeNET score, see
    https://www.disgenet.org/dbinfo#score

    """

    if nodes is None:
        nodes = ["disorder", "drug", "gene", "protein"]
    if edges is None:
        edges = [
            "disorder_is_subtype_of_disorder",
            "drug_has_indication",
            "drug_has_target",
            "gene_associated_with_disorder",
            "protein_encoded_by_gene",
            "protein_interacts_with_protein",
        ]
    if ppi_evidence is None:
        ppi_evidence = ["exp"]
    if taxid is None:
        taxid = [9606]
    if drug_groups is None:
        drug_groups = ["approved"]

    body = {
        "nodes": nodes,
        "edges": edges,
        "ppi_evidence": ppi_evidence,
        "ppi_self_loops": include_ppi_self_loops,
        "taxid": taxid,
        "drug_groups": drug_groups,
        "concise": concise,
        "include_omim": include_omim,
        "disgenet_threshold": disgenet_threshold,
        "use_omim_ids": use_omim_ids,
        "split_drug_types": split_drug_types,
    }

    if reviewed_proteins is not None:
        body["reviewed_proteins"] = reviewed_proteins

    url = f"{_config.url_base}/graph/builder"
    resp = _http.post(url, json=body, headers={"x-api-key": _config.api_key})
    result: str = _check_response(resp)
    return result


# pylint: enable=R0913


def check_build_status(uid: str) -> _Dict[str, _Any]:
    """Returns the details of a submitted graph build job

    Parameters
    ----------
    uid : str
        The unique ID of a graph build job

    Returns
    -------
    dict[str, Any]
        Details of the graph build job with the given unique ID; the
        status of the job is stored using the `status` key
    """
    url = f"{_config.url_base}/graph/details/{uid}"
    resp = _http.get(url, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _Any] = _check_response(resp)
    return result


def download_graph(uid: str, target: _Optional[str] = None, filename: _Optional[str] = None) -> str:
    """Downloads the resultant graph of a submitted graph build job

    Parameters
    ----------
    uid : str
        The unique ID of a graph build job
    target : str, optional
        The target file path for the downloaded data. If not specified,
        this defaults to <cwd>/<uid>.graphml
    filename : str, optional
        Attachment name without .graphml (default: uid, as before).

    Returns
    -------
    str
        The path to which the downloaded data was saved.
    """
    if target is None:
        target = str(_Path(f"{uid}.graphml").resolve())

    suffix = _quote(uid, safe="") + "/" + _quote(filename or uid, safe="") + ".graphml"
    url = f"{_config.url_base}/graph/download/{suffix}"

    _download_file(url, target)
    return target
