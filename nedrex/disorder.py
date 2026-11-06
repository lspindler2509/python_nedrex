"""Module containing python functions to access the disorder routes in the NeDRex API"""

from typing import Any as _Any
from typing import Callable as _Callable
from typing import List as _List
from typing import Union as _Union

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import http as _http
from nedrex._decorators import check_url_base as _check_url_base

__all__ = [
    "search_by_icd10",
    "get_disorder_descendants",
    "get_disorder_ancestors",
    "get_disorder_parents",
    "get_disorder_children",
]


def _generate_route(path: str) -> _Callable[[_Union[str, _List[str]]], _Any]:
    @_check_url_base
    def new_func(codes: _Union[str, _List[str]]) -> _Any:
        if isinstance(codes, str):
            codes = [codes]

        url = f"{_config.url_base}/disorder/{path}"
        resp = _http.get(url, params={"q": codes}, headers={"x-api-key": _config.api_key})
        items = _check_response(resp)
        return items

    return new_func


search_by_icd10 = _generate_route("get_by_icd10")
search_by_icd10.__name__ = "search_by_icd10"
search_by_icd10.__doc__ = """Obtains NeDRex disorder nodes by ICD-10 codes

    Parameters
    ----------
    codes : str | list[str]
        An ICD-10 code (or list of ICD-10 codes) to search for in NeDRexDB

    Returns
    -------
    list[dict[str, Any]]
        Disorder records from NeDRexDB
"""

get_disorder_descendants = _generate_route("descendants")
get_disorder_descendants.__name__ = "get_disorder_descendants"
get_disorder_descendants.__doc__ = """Returns the ID(s) of nodes that are descentants of the input ID(s)

    Parameters
    ----------
    codes : str | list[str]
        A disorder ID (or list of disorder IDs) to get the descendants of.
        Note that this can be in any valid namespace (e.g., mesh.D006980).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps the input terms (in MONDO ID space) to a
        list of their descendants. This means that input IDs in a non
        MONDO namespace will not appear in the result (see example).

    Examples
    --------
    >>> get_disorder_descendants("mesh.D006980")
    {'mondo.0004425': ['mondo.0001104',
     'mondo.0001252',
     'mondo.0001555',
     'mondo.0005364',
     'mondo.0006996',
     'mondo.0007784',
     'mondo.0008569',
     'mondo.0009043',
     'mondo.0010131',
     'mondo.0010138',
     'mondo.0010304',
     'mondo.0011309',
     'mondo.0011314',
     'mondo.0012203',
     'mondo.0014448',
     'mondo.0019854',
     'mondo.0019855',
     'mondo.0019860',
     'mondo.0019861',
     'mondo.0033925']}
"""

get_disorder_ancestors = _generate_route("ancestors")
get_disorder_ancestors.__name__ = "get_disorder_ancestors"
get_disorder_ancestors.__doc__ = """Returns the ID(s) of nodes that are ancestors of the input ID(s)

    Parameters
    ----------
    codes : str | list[str]
        A disorder ID (or list of disorder IDs) to get the ancestors of.
        Note that this can be in any valid namespace (e.g., mesh.D006980).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps the input terms (in MONDO ID space) to a
        list of their ancestors. This means that input IDs in a non-MONDO
        namespace will not appear in the result (see example).

    Examples
    --------
    >>> get_disorder_ancestors("mesh.D006980")
    {'mondo.0004425': ['mondo.0000001', 'mondo.0003240', 'mondo.0005151']}
"""

get_disorder_parents = _generate_route("parents")
get_disorder_parents.__name__ = "get_disorder_parents"
get_disorder_parents.__doc__ = """Returns the ID(s) of nodes that are parents of the input ID(s)

    Parameters
    ----------
    codes : str | list[str]
        A disorder ID (or list of disorder IDs) to get the parents of.
        Note that this can be in any valid namespace (e.g., mesh.D006980).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps the input terms (in MONDO ID space) to a
        list of their parents. This means that input IDs in a non-MONDO
        namespace will not appear in the result (see example).

    Examples
    --------
    >>> get_disorder_parents("mesh.D006980")
    {'mondo.0004425': ['mondo.0003240']}

"""

get_disorder_children = _generate_route("children/")
get_disorder_children.__name__ = "get_disorder_children"
get_disorder_children.__doc__ = """Returns the ID(s) of nodes that are children of the input ID(s)

    Parameters
    ----------
    codes : str | list[str]
        A disorder ID (or list of disorder IDs) to get the children of.
        Note that this can be in any valid namespace (e.g., mesh.D006980).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps the input terms (in MONDO ID space) to a
        list of their children. This means that input IDs in a non-MONDO
        namespace will not appear in the result (see example).

    Examples
    --------
    >>> get_disorder_children("mesh.D006980")
    {'mondo.0004425': ['mondo.0001104',
     'mondo.0001252',
     'mondo.0006996',
     'mondo.0007784',
     'mondo.0009043',
     'mondo.0011309',
     'mondo.0012203',
     'mondo.0014448']}
"""
