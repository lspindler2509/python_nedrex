# -*- coding: utf-8 -*-
"""Functions to use the BiCoN routes in a NeDRex API instance

This module contains the following functions:
    * bicon_request - submits a request to NeDRex to run BiCoN
    * check_bicon_status - gets details of a submitted BiCoN job
    * download_bicon_data - download results for a completed BiCoN job
"""

from pathlib import Path as _Path
from typing import IO as _IO
from typing import Any as _Any
from typing import Dict as _Dict
from typing import Optional as _Optional

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import download_file as _download_file
from nedrex._common import http as _http


def bicon_request(expression_file: _IO[str], lg_min: int = 10, lg_max: int = 15, network: str = "DEFAULT") -> str:
    """Submits a request to NeDRex to run BiCoN and returns the job UID

    Parameters
    ----------
    expression_file : IO[str]
        A handle to an IO object (e.g., open file) containing expression
        data
    lg_min : int, optional
        The minimum desired size of the solution subnetworks (the default
        is 10)
    lg_max : int, optional
        The maximum desired size of the solution subnetworks (the default
        is 15)
    network : str, optional
        The GGI network to use for running BiCoN (default is "DEFAULT",
        which is a PPI-based GGI network)

    Returns
    -------
    str
        The unique ID of the submitted BiCoN job
    """
    files = {"expression_file": expression_file}
    data = {"lg_min": lg_min, "lg_max": lg_max, "network": network}

    url = f"{_config.url_base}/bicon/submit"
    resp = _http.post(url, data=data, files=files, headers={"x-api-key": _config.api_key})
    result: str = _check_response(resp)
    return result


def check_bicon_status(uid: str) -> _Dict[str, _Any]:
    """Gets the status of a submitted BiCoN job

    Parameters
    ----------
    uid : str
        The unique ID of a BiCoN job

    Returns
    -------
    dict[str, Any]
        Details of the current BiCoN job; the status of job is stored
        using the `status` key
    """
    url = f"{_config.url_base}/bicon/status"
    resp = _http.get(url, params={"uid": uid}, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _Any] = _check_response(resp)
    return result


def download_bicon_data(uid: str, target: _Optional[str] = None) -> str:
    """Downloads results for a submitted BiCoN job

    Parameters
    ----------
    uid : str
        The unique ID of a BiCoN job
    target : str, optional
        The target file path for the downloaded data. If not specified,
        this defaults <cwd>/<uid>.zip

    Returns
    -------
    str
        The path to which the downloaded data was saved.
    """
    if target is None:
        target = str(_Path(f"{uid}.zip").resolve())

    url = f"{_config.url_base}/bicon/download?uid={uid}"

    _download_file(url, target)
    return target


def download_bicon_clustermap(uid: str, target: _Optional[str] = None) -> str:
    """Download a completed job's PNG clustermap; default target is <uid>-clustermap.png."""
    if target is None:
        target = str(_Path("{}-clustermap.png".format(uid)).resolve())
    from urllib.parse import urlencode

    _download_file(_config.url_base + "/bicon/clustermap?" + urlencode({"uid": uid}), target)
    return target
