# -*- coding: utf-8 -*-
"""Code to access static data in the NeDRex API
"""

from typing import Any as _Any
from typing import Dict as _Dict
from typing import Optional as _Optional

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import download_file as _download_file
from nedrex._common import http as _http
from nedrex._common import request as _request


def get_metadata() -> _Dict[str, _Any]:
    """Obtains metadata from NeDRexDB

    The metadata contains the versions (or dates obtained) of the individual
    source databases integrated into NeDRexDB.

    Returns
    -------
    dict[str, Any]
        The metadata for the NeDRexDB instance behind the API
    """
    url = f"{_config.url_base}/static/metadata"
    resp = _http.get(url, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _Any] = _check_response(resp)
    return result


def get_license() -> str:
    """Obtain the NeDRex license

    Returns
    -------
    str
        The text of the NeDRex license.
    """
    url = f"{_config.url_base}/static/licence"
    resp = _http.get(url)
    result: str = _check_response(resp=resp, return_type="text")
    return result


def download_lengths_map(target: _Optional[str] = None) -> None:
    """Obtains the lengths.map file

    The lengths.map file is required for some versions of the NeDRex app.

    Parameters
    ----------
    target : str, optional
        The file location to save the file, with the default being lengths.map
        in the current directory.
    """
    if target is None:
        target = "lengths.map"

    url = f"{_config.url_base}/static/lengths.map"

    _download_file(url, target)


def get_icd10_omim_map() -> str:
    """Return the static ICD-10 to OMIM mapping as tab-separated text (not JSON)."""
    return _request("/static/icd10_omim_map", return_type="text")


def get_icd10_mondo_map() -> str:
    """Return the static ICD-10 to MONDO mapping as tab-separated text (not JSON)."""
    return _request("/static/icd10_mondo_map", return_type="text")
