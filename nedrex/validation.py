# -*- coding: utf-8 -*-
"""Functions to run the validation routes of a NeDRex API instance
"""

from typing import List as _List
from typing import Tuple as _Tuple
from typing import Union as _Union

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import check_status_factory as _check_status_factory
from nedrex._common import http as _http

__all__ = ["joint_validation_submit", "module_validation_submit", "drug_validation_submit", "check_validation_status"]

check_validation_status = _check_status_factory("/validation/status")
check_validation_status.__name__ = "check_validation_status"
check_validation_status.__doc__ = """Gets details of a validation job

    Parameters
    ----------
    uid : str
        The unique ID of a validation job

    Returns
    -------
    dict[str, Any]
        Details of the validation job; the status of job is stored using the
        `status` key
"""


def check_module_member_type(mmt: str) -> None:
    """Checks the module member type submitted to a validation request

    Parameters
    ----------
    mmt : str
        The module member type, should be "gene" or "protein"

    Raises
    ------
    ValueError
        Raised if the module member type is not "gene" or "protein"
    """
    if mmt not in {"gene", "protein"}:
        raise ValueError(f"module_member_type {mmt!r} is invalid (should be 'gene' or 'protein'")


# pylint: disable=R0913
def joint_validation_submit(
    module_members: _List[str],
    module_member_type: str,
    test_drugs: _List[str],
    true_drugs: _List[str],
    permutations: int,
    only_approved_drugs: bool = True,
) -> str:
    """Joint validation of disease modules and drug lists computed by NeDRex

    Parameters
    ----------
    module_members : list[str]
        The members of the disease module predicted by NeDRex
    module_member_type : str
        The type of the module members (should be `drug` or `gene`)
    test_drugs : list[str]
        The drugs that were predicted by a NeDRex drug repurposing algorithm
    true_drugs : list[str]
        A list of drugs that are indicated for the disorder
    permutations : int
        The number of permutations to run in validation
    only_approved_drugs : bool:
        Whether to use approved drugs only (True) or all drugs (False). Default
        is True

    Returns
    -------
    str
        The UID of the joint validation job
    """
    check_module_member_type(module_member_type)

    url = f"{_config.url_base}/validation/joint"
    body = {
        "module_members": module_members,
        "module_member_type": module_member_type,
        "test_drugs": test_drugs,
        "true_drugs": true_drugs,
        "permutations": permutations,
        "only_approved_drugs": only_approved_drugs,
    }
    resp = _http.post(url, json=body, headers={"x-api-key": _config.api_key})
    result: str = _check_response(resp)
    return result


# pylint: enable=R0913


def module_validation_submit(
    module_members: _List[str],
    module_member_type: str,
    true_drugs: _List[str],
    permutations: int,
    only_approved_drugs: bool = True,
) -> str:
    """Validation of disease modules computed by NeDRex

    Parameters
    ----------
    module_members : list[str]
        The module members predicted by NeDRex
    module_member_type : str
        The type of the module members (should be `drug` or `gene`)
    true_drugs : list[str]
        A list of drugs that are indicated for the disorder
    permutations : int
        The number of permutations to run in validation
    only_approved_drugs : bool, optional
        Whether to use approved drugs only (True) or all drugs (False). Default
        is True

    Returns
    -------
    str
        The UID of the joint validation job
    """
    check_module_member_type(module_member_type)

    url = f"{_config.url_base}/validation/module"
    body = {
        "module_members": module_members,
        "module_member_type": module_member_type,
        "true_drugs": true_drugs,
        "permutations": permutations,
        "only_approved_drugs": only_approved_drugs,
    }
    resp = _http.post(url, json=body, headers={"x-api-key": _config.api_key})
    result: str = _check_response(resp)
    return result


def drug_validation_submit(
    test_drugs: _Union[_List[str], _List[_Tuple[str, float]]],
    true_drugs: _List[str],
    permutations: int,
    only_approved_drugs: bool = True,
) -> str:
    """Validation of drug lists computed by NeDRex

    Parameters
    ----------
    test_drugs : list[str] or list[tuple[str, float]]
        Drug IDs for legacy servers, or ID/score pairs for current servers,
        e.g. [("DB00001", 0.5)]. Passed through without changing their meaning.
    true_drugs : list[str]
        A list of drugs that are indicated for the disorder
    permutations : int
        The number of permutations to run in validation
    only_approved_drugs : bool, optional
        Whether to use approved drugs only (True) or all drugs (False). Default
        is True

    Returns
    -------
    str
        The UID of the joint validation job
    """

    url = f"{_config.url_base}/validation/drug"
    body = {
        "test_drugs": test_drugs,
        "true_drugs": true_drugs,
        "permutations": permutations,
        "only_approved_drugs": only_approved_drugs,
    }

    resp = _http.post(url, json=body, headers={"x-api-key": _config.api_key})
    result: str = _check_response(resp)
    return result
