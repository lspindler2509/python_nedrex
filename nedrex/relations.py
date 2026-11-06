import warnings as _warnings
from typing import Dict as _Dict
from typing import Iterable as _Iterable
from typing import List as _List
from typing import Union as _Union

from nedrex import config as _config
from nedrex._common import check_response as _check_response
from nedrex._common import http as _http


def get_encoded_proteins(gene_list: _Iterable[_Union[int, str]]) -> _Dict[str, _List[str]]:
    """Gets the proteins that are encoded by genes in a supplied gene list

    Parameters
    ----------
    gene_list : iterable[str | int]
        A list of genes to get the encoded protein for. These genes should
        be Entrez gene IDs, and can be provided as either a string or an
        integer. The may optionally be prefixed with "entrez.", but this
        is not required.

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps gene IDs to lists of encoded proteins.
        It should be noted that genes IDs are convered to string in the
        resultant dictionary, and they *do not* have the `entrez.` prefix.
        Additionally, the protein IDs *do not* have the `uniprot.` prefix.
    """
    genes = []
    for gene in gene_list:
        if isinstance(gene, int):
            gene = str(gene)
        if not isinstance(gene, str):
            raise ValueError("items in gene_list must be int or str")

        gene = gene.lower()
        if not gene.startswith("entrez."):
            genes.append(f"entrez.{gene}")
        else:
            genes.append(gene)

    url = f"{_config.url_base}/relations/get_encoded_proteins"
    resp = _http.post(url, json={"nodes": genes}, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _List[str]] = _check_response(resp)
    return result


def get_drugs_indicated_for_disorders(disorder_list: _Iterable[str]) -> _Dict[str, _List[str]]:
    """Gets the drugs that are indicated for supplied disorders

    Parameters
    ----------
    disorder_list : iterable[str]
        A list of disorders to get indicated drugs for. Disorder IDs
        should be provided in the MONDO namespace, and may optionally be
        prefixed with `mondo.` (but this is not required).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps disorder IDs to lists of indicated drugs.
        It should be noted that disorder IDs in the resultant dictionary
        *do not* have the `mondo.` prefix. Additionally, drug IDs *do not*
        have a `drugbank.` prefix.
    """
    disorders = []
    for disorder in disorder_list:
        if not isinstance(disorder, str):
            raise ValueError("items in disorder_list must be str")

        if disorder.startswith("mondo."):
            disorders.append(disorder)
        else:
            disorders.append(f"mondo.{disorder}")

    url = f"{_config.url_base}/relations/get_drugs_indicated_for_disorders"
    resp = _http.post(url, json={"nodes": disorders}, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _List[str]] = _check_response(resp)
    return result


def get_drugs_targeting_proteins(protein_list: _Iterable[str]) -> _Dict[str, _List[str]]:
    """Gets drugs that target proteins in a supplied protein list

    Parameters
    ----------
    protein_list : iterable[str]
        A list of protein IDs to get targetting drugs for. Protein IDs
        should be provided in the UniProt namespace, and may optionally be
        prefixed with `uniprot.` (but this is not required).

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps protein IDs to lists of the drugs that
        target them. It should be noted that protein IDs in the resultant
        dictionary *do not* have the `uniprot.` prefix. Additionally, drug
        IDs do not have a `drugbank.` prefix.
    """
    proteins = []
    for protein in protein_list:
        if not isinstance(protein, str):
            raise ValueError("items in protein_list must be str")

        if protein.startswith("uniprot."):
            proteins.append(protein)
        else:
            proteins.append(f"uniprot.{protein}")

    url = f"{_config.url_base}/relations/get_drugs_targeting_proteins"
    resp = _http.post(url, json={"nodes": proteins}, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _List[str]] = _check_response(resp)
    return result


def get_drugs_targeting_gene_products(gene_list: _Iterable[_Union[int, str]]) -> _Dict[str, _List[str]]:
    """Get drugs that target the products of genes in a supplied gene list

    Parameters
    ----------
    gene_list : iterable[str | int]
        A list of genes. These genes should be Entrez gene IDs, and can be
        provided as either a string or an integer. The may optionally be
        prefixed with "entrez.", but this is not required.

    Returns
    -------
    dict[str, list[str]]
        A dictionary that maps gene IDs to lists of drugs which target
        the protein products of the gene. It should be noted that gene IDs
        are converted to strings in the resultant dictionary, and they
        *do not* have the `entrez.` prefix. Additionally, drug IDs do not
        have a `drugbank.` prefix.
    """
    genes = []
    for gene in gene_list:
        if isinstance(gene, int):
            gene = str(gene)
        if not isinstance(gene, str):
            raise ValueError("items in gene_list must be int or str")

        gene = gene.lower()
        if not gene.startswith("entrez."):
            genes.append(f"entrez.{gene}")
        else:
            genes.append(gene)

    url = f"{_config.url_base}/relations/get_drugs_targeting_gene_products"
    resp = _http.post(url, json={"nodes": genes}, headers={"x-api-key": _config.api_key})
    result: _Dict[str, _List[str]] = _check_response(resp)
    return result


def get_drugs_targetting_proteins(protein_list: _Iterable[str]) -> _Dict[str, _List[str]]:
    """Deprecated alias for get_drugs_targeting_proteins (misspelled name used in 0.1.4)."""
    _warnings.warn(
        "get_drugs_targetting_proteins is deprecated; use get_drugs_targeting_proteins",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_drugs_targeting_proteins(protein_list)


def get_drugs_targetting_gene_products(gene_list: _Iterable[_Union[int, str]]) -> _Dict[str, _List[str]]:
    """Deprecated alias for get_drugs_targeting_gene_products (misspelled name used in 0.1.4)."""
    _warnings.warn(
        "get_drugs_targetting_gene_products is deprecated; use get_drugs_targeting_gene_products",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_drugs_targeting_gene_products(gene_list)
