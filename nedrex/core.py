"""Module containing functions relating to the general routes in the NeDRex API

This module contains functions that access the general routes, and also routes
for obtaining API keys.
"""

from typing import Any as _Any
from typing import Dict as _Dict
from typing import Generator as _Generator
from typing import List as _List
from typing import Optional as _Optional
from typing import cast as _cast
from urllib.parse import quote as _quote

from nedrex import config as _config
from nedrex._common import check_pagination_limit as _check_pagination_limit
from nedrex._common import check_response as _check_response
from nedrex._common import get_pagination_limit as _get_pagination_limit
from nedrex._common import http as _http
from nedrex._common import iter_pages as _iter_pages
from nedrex._common import request as _request
from nedrex._decorators import check_url_base as _check_url_base
from nedrex.exceptions import NeDRexError as _NeDRexError


def _check_type(coll_name: str, coll_type: str) -> bool:
    if coll_type == "edge":
        if coll_name in get_edge_types():
            return True
        raise _NeDRexError(f"type={coll_name!r} not in NeDRex edge types")

    if coll_type == "node":
        if coll_name in get_node_types():
            return True
        raise _NeDRexError(f"type={coll_name!r} not in NeDRex node types")

    raise _NeDRexError(f"_check_type received invalid coll_type={coll_type!r}")


@_check_url_base
def api_keys_active() -> bool:
    """Checks whether API keys are active for the instance of NeDRex set in the config

    Returns
    -------
    bool
        True if the API keys are required, otherwise False.
    """
    url = f"{_config.url_base}/api_key_setting"
    response = _http.get(url)
    if response.status_code != 200:
        raise Exception("Unexpected non-200 status code")
    active = _cast(bool, response.json())
    return active


@_check_url_base
def get_api_key(*, accept_eula: bool = False) -> str:
    """Obtains a new API key for the NeDRex API.

    Parameters
    ----------
    accept_eula : bool
        Parameter reflecting whether the user of the library accepts
        the terms of the NeDRex end user licence agreement (EULA).
        Defaults to False. Must be set to True to acquire an API key.

    Returns
    -------
    str
        An API key that can be used to access the NeDRex platform.
    """
    if accept_eula is not True:
        raise _NeDRexError("an API key cannot be obtained unless accept_eula is set to True")

    url = f"{_config.url_base}/admin/api_key/generate"
    response = _http.post(url, json={"accept_eula": accept_eula})
    api_key = _cast(str, _check_response(response))
    return api_key


@_check_url_base
def get_pagination_limit() -> int:
    """Gets the pagination limit for the NeDRexDB instance

    Returns
    -------
    int
        The pagination limit for the NeDRexDB instance
    """
    limit: int = _get_pagination_limit()
    return limit


@_check_url_base
def get_node_types() -> _List[str]:
    """Gets a list of the node types stored in NeDRexDB

    Returns
    -------
    list[str]
        A list of node types in NeDRexDB
    """
    url: str = f"{_config.url_base}/list_node_collections"
    response = _http.get(url, headers={"x-api-key": _config.api_key})
    node_list = _cast(_List[str], _check_response(response))
    return node_list


@_check_url_base
def get_edge_types() -> _List[str]:
    """Gets a list of the edge types stored in NeDRexDB

    Returns
    -------
    list[str]
        A list of edge types in NeDRexDB
    """
    url: str = f"{_config.url_base}/list_edge_collections"
    response = _http.get(url, headers={"x-api-key": _config.api_key})
    edge_list = _cast(_List[str], _check_response(response))
    return edge_list


@_check_url_base
def get_collection_attributes(coll_type: str, include_counts: bool = False) -> _Any:
    """Gets the available attributes in NeDRex for the given type

    Parameters
    ----------
    coll_type: str
        The name of the collection
    include_counts: bool, optional
        If True, returns the counts for each attribute. If False, just
        returns a list of the attributes. Default is False.

    Returns
    -------
    Union[Dict[str, Any], List[str]]
        If include_counts is False, this returns a list of the attributes
        that members of the collections have. If include_counts is true,
        this returns a dictionary that includes the counts.

    Examples
    --------
    >>> get_collection_attributes(protein)
    ['primaryDomainId',
     'comments',
     'created',
     'dataSources',
     'displayName',
     'domainIds',
     'geneName',
     'sequence',
     'synonyms',
     'taxid',
     'type',
     'updated']

    >>> get_collection_attributes(protein, include_counts=True)
    {'attribute_counts': {'comments': 204906,
                          'created': 204906,
                          'dataSources': 204906,
                          'displayName': 204906,
                          'domainIds': 204906,
                          'geneName': 204906,
                          'primaryDomainId': 204906,
                          'sequence': 204906,
                          'synonyms': 204906,
                          'taxid': 204906,
                          'type': 204906,
                          'updated': 204906},
     'document_count': 204906}
    """
    url: str = f"{_config.url_base}/{coll_type}/attributes"
    response = _http.get(url, headers={"x-api-key": _config.api_key}, params={"include_counts": include_counts})
    attributes = _check_response(response)
    return attributes


@_check_url_base
def get_node_ids(coll_type: str) -> _Any:
    """Returns a list of node identifiers in NeDRex for the given type

    Parameters
    ----------
    coll_type: str
        The node type to get IDs for

    Returns
    -------
    list[str]
        The list of available node IDs for the specificed node type
    """
    _check_type(coll_type, "node")

    url: str = f"{_config.url_base}/{coll_type}/attributes/primaryDomainId/json"

    resp = _http.get(url, headers={"x-api-key": _config.api_key})
    data = _check_response(resp)
    node_ids = [i["primaryDomainId"] for i in data]
    return node_ids


@_check_url_base
def get_nodes(
    node_type: str,
    attributes: _Optional[_List[str]] = None,
    node_ids: _Optional[_List[str]] = None,
    limit: _Optional[int] = None,
    offset: int = 0,
    fmt: str = "json",
) -> _Any:
    """Returns nodes in NeDRex of the given type

    Parameters
    ----------
    node_type : str
        The node type to collect
    attributes : list[str], optional
        A list of attributes to return for the collected nodes. The
        default, None, returns all attributes.
    node_ids : list[str], optional
        A list of IDs of specific nodes to be returned. The default (None)
        does no filtering by node ID. Explicit IDs are sent via POST.
    limit : int, optional
        A limit for the number of records to be returned. The default is
        determined by querying the API.
    offset : int, optional
        The number of records to skip before returning records. Default is
        0 (no records skipped).

    fmt : str, optional
        Output format: json (native data) or tsv (text). Default is json.

    Returns
    -------
    list[dict[str, Any]]
        The nodes returned by the API; TSV format returns str instead.
    """
    _check_type(node_type, "node")
    if node_ids or fmt != "json":
        return _get_attributes(node_type, attributes, node_ids, limit=limit, offset=offset, fmt=fmt)

    upper_limit = _get_pagination_limit()
    _check_pagination_limit(limit, upper_limit)

    params = {"node_id": node_ids, "attribute": attributes, "offset": offset, "limit": limit}

    resp = _http.get(
        f"{_config.url_base}/{node_type}/attributes/json", params=params, headers={"x-api-key": _config.api_key}
    )

    items = _check_response(resp)
    return items


@_check_url_base
def iter_nodes(
    node_type: str,
    attributes: _Optional[_List[str]] = None,
    node_ids: _Optional[_List[str]] = None,
    page_size: _Optional[int] = None,
    offset: int = 0,
    max_records: _Optional[int] = None,
) -> _Generator[_Dict[str, _Any], None, None]:
    """A function that returns a generator to iterate over nodes

    This function is useful if you wish to get all nodes in a particular
    collection, but do not want to manually handle offsets and limits.

    Parameters
    ----------
    node_type : str
        The node type to collect
    attributes : list[str], optional
        A list of attributes to return for the collected nodes. The
        default, None, returns all attributes.
    node_ids : list[str], optional
        A list of IDs of specific nodes to be returned. The default (None)
        does no filtering by node ID. Explicit IDs are sent via POST.


    page_size : int, optional
        Records per request (default: instance maximum).
    offset : int, optional
        Initial matching-record offset (default: 0).
    max_records : int, optional
        Maximum total records to yield; None reads all pages.


    Yields
    ------
    dict[str, Any]
        A node in NeDRex returned by the API
    """
    _check_type(node_type, "node")
    yield from _iter_pages(
        lambda **page: _get_attributes(node_type, attributes, node_ids, **page),
        page_size,
        offset,
        max_records,
    )


@_check_url_base
def get_edges(
    edge_type: str,
    limit: _Optional[int] = None,
    offset: _Optional[int] = None,
    attributes: _Optional[_List[str]] = None,
    source_domain_ids: _Optional[_List[str]] = None,
    target_domain_ids: _Optional[_List[str]] = None,
    fmt: str = "json",
) -> _Any:
    """
    Returns edges in NeDRex of the given type

    Parameters
    ----------
    edge_type : str
        The edge type to collect
    limit : int, optional
        A limit for the number of records to be returned. The default is
        determined by querying the API.
    offset : int, optional
        The number of records to skip before returning records. Default is
        0 (no records skipped).

    attributes : list[str], optional
        Select fields via the attributes route; None keeps the existing /all route
        unless another filter, format or POST option is supplied.
    source_domain_ids, target_domain_ids : list[str], optional
        Filter edges by source or target IDs; non-empty ID filters use POST.
    fmt : str, optional
        Output format: json (native data) or tsv (text). Default is json.

    Returns
    -------
    list[dict[str, Any]]
        The edges returned by the API; TSV format returns str instead.
    """
    _check_type(edge_type, "edge")
    if attributes is not None or source_domain_ids is not None or target_domain_ids is not None or fmt != "json":
        return _get_attributes(
            edge_type,
            attributes,
            source_domain_ids=source_domain_ids,
            target_domain_ids=target_domain_ids,
            limit=limit,
            offset=0 if offset is None else offset,
            fmt=fmt,
        )

    params = {"limit": limit, "offset": offset, "api_key": _config.api_key}

    resp = _http.get(f"{_config.url_base}/{edge_type}/all", params=params, headers={"x-api-key": _config.api_key})
    items = _check_response(resp)
    return items


@_check_url_base
def iter_edges(
    edge_type: str,
    page_size: _Optional[int] = None,
    offset: int = 0,
    max_records: _Optional[int] = None,
    attributes: _Optional[_List[str]] = None,
    source_domain_ids: _Optional[_List[str]] = None,
    target_domain_ids: _Optional[_List[str]] = None,
) -> _Generator[_Dict[str, _Any], None, None]:
    """A function that returns a generator to iterate over edges

    This function is useful if you wish to get all edges in a particular
    collection, but do not want to manually handle offsets and limits.

    Parameters
    ----------
    edge_type : str
        The edge type to collect

    page_size : int, optional
        Records per request (default: instance maximum).
    offset : int, optional
        Initial matching-record offset (default: 0).
    max_records : int, optional
        Maximum total records to yield; None reads all pages.

    attributes : list[str], optional
        Select fields; filters have the same meaning as in get_edges.
    source_domain_ids, target_domain_ids : list[str], optional
        Filter by source or target IDs on every page.

    Yields
    ------
    dict[str, Any]
        An edge in NeDRex returned by the API
    """
    _check_type(edge_type, "edge")
    yield from _iter_pages(
        lambda **page: get_edges(
            edge_type,
            attributes=attributes,
            source_domain_ids=source_domain_ids,
            target_domain_ids=target_domain_ids,
            **page,
        ),
        page_size,
        offset,
        max_records,
    )


@_check_url_base
def get_collection_details(collection: str) -> _Any:
    """Return collection details and counts from /{collection}/details."""
    return _request("/{}/details".format(_quote(collection, safe="")))


@_check_url_base
def get_attribute_values(collection: str, attribute: str, fmt: str = "json") -> _Any:
    """Return one attribute for a collection, in the server's json or tsv format.

    This route has no pagination controls; prefer get_nodes/get_edges for bounded calls.
    JSON returns native data; TSV returns text.
    """
    return _request(
        "/{}/attributes/{}/{}".format(_quote(collection, safe=""), _quote(attribute, safe=""), _quote(fmt, safe="")),
        return_type="json" if fmt == "json" else "text",
    )


def _get_attributes(
    collection: str,
    attributes: _Optional[_List[str]] = None,
    node_ids: _Optional[_List[str]] = None,
    source_domain_ids: _Optional[_List[str]] = None,
    target_domain_ids: _Optional[_List[str]] = None,
    limit: _Optional[int] = None,
    offset: int = 0,
    fmt: str = "json",
) -> _Any:
    """Return one filtered attribute page for nodes or edges.

    attributes/node_ids select fields and nodes; source_domain_ids/target_domain_ids
    select edge endpoints. ID filters automatically use POST (skip=offset).
    fmt is the native json or tsv format. Iterators use JSON. Unset fields are omitted.
    """
    _check_pagination_limit(limit, _get_pagination_limit())
    if offset < 0:
        raise _NeDRexError("offset must be non-negative")
    path = "/{}/attributes/{}".format(_quote(collection, safe=""), _quote(fmt, safe=""))
    filters = {"source_domain_id": source_domain_ids, "target_domain_id": target_domain_ids, "limit": limit}
    if node_ids or source_domain_ids or target_domain_ids:
        filters.update(attributes=attributes or [], node_ids=node_ids, skip=offset)
        return _request(path, "post", json=filters, return_type="json" if fmt == "json" else "text")
    filters.update(attribute=attributes, node_id=node_ids, offset=offset)
    return _request(path, params=filters, return_type="json" if fmt == "json" else "text")


@_check_url_base
def get_by_id(collection: str, query: str) -> _Any:
    """Look up one primary/external ID using the public API's path-based route.

    IDs must carry their namespace (e.g. uniprot.P00533); bare identifiers return an
    empty list.
    """
    return _request("/get_by_id/{}/{}".format(_quote(collection, safe=""), _quote(query, safe="")))


@_check_url_base
def find_by_ids(collection: str, node_ids: _List[str]) -> _Any:
    """Bulk lookup via POST /find_by_ids/ (public API; not available on every instance)."""
    return _request("/find_by_ids/", "post", json={"collection_name": collection, "id_list": node_ids})


@_check_url_base
def map_ids(collection: str, identifiers: _List[str]) -> _Any:
    """Map namespaced identifiers (e.g. uniprot.P00533) to primaryDomainId lists.

    Ambiguous matches and nulls for unknown identifiers are retained from the API.
    """
    return _request("/id_map/{}".format(_quote(collection, safe="")), params={"q": identifiers})


@_check_url_base
def entrez_to_uniprot_id(query: str) -> _Any:
    """Map one Entrez identifier via GET /entrez_to_uniprot_id (public API)."""
    return _request("/entrez_to_uniprot_id", params={"q": query})


@_check_url_base
def entrez_to_uniprot_ids(ids: _List[str]) -> _Any:
    """Map multiple Entrez identifiers via POST /entrez_to_uniprot_ids (public API)."""
    return _request("/entrez_to_uniprot_ids", "post", json={"ids": ids})
