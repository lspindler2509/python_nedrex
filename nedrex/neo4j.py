# -*- coding: utf-8 -*-
"""Module containing a function providing access to Neo4j NeDRex
"""

import json as _json
from typing import Any as _Any
from typing import Dict as _Dict
from typing import Generator as _Generator
from typing import List as _List
from typing import Optional as _Optional
from urllib.parse import quote as _quote

from requests.exceptions import ChunkedEncodingError  # type: ignore

from nedrex import config as _config
from nedrex._common import download_file as _download_file
from nedrex._common import http as _http
from nedrex._common import request as _request
from nedrex.exceptions import NeDRexError


def neo4j_query(query: str) -> _Generator[_List[_Dict[str, _Any]], None, None]:
    """Run a cypher query on a Neo4j NeDRex instance

    Parameters
    ----------
    query : str
        A valid cypher query

    Yields
    ------
    list[dict[str, Any]]
        An individual result from the cypher query.
    """
    url = f"{_config.url_base}/neo4j/query"
    resp = _http.post(
        url, json={"query": query, "stream": True}, headers={"x-api-key": _config.api_key}, stream=True
    )
    if resp.status_code != 200:
        raise NeDRexError("Querying Neo4j returned a non-200 status code.")

    try:
        for line in resp.iter_lines():
            data = _json.loads(line.decode())
            yield from data

    except ChunkedEncodingError as exc:
        raise NeDRexError("cypher query could not be executed") from exc


def query(query: str, download: bool = False) -> _Any:
    """Run non-streaming Cypher, or submit a server download job with download=True.

    Returns the native JSON result or job UID. Jobs can be inspected using
    check_query_status and downloaded using download_query_results. POST and
    download jobs are instance-dependent; TUM currently exposes only GET streaming.
    """
    body = {"query": query, "stream": False, "download": download}
    return _request("/neo4j/query", "post", json=body)


def check_query_status(uid: str) -> _Any:
    """Return the status/details of a Neo4j download job (public API)."""
    return _request("/neo4j/details/{}".format(_quote(uid, safe="")))


def download_query_results(uid: str, target: _Optional[str] = None) -> str:
    """Download a Neo4j job's JSON file; default target is <uid>.json."""
    if target is None:
        target = uid + ".json"
    _download_file(_config.url_base + "/neo4j/download/" + _quote(uid, safe="") + ".json", target)
    return target
