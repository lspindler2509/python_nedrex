#!/usr/bin/env python

"""Tests for `nedrex` package."""

import os
import re
from pathlib import Path
import random
import tempfile
import time
from contextlib import contextmanager
from functools import lru_cache

from more_itertools import take

import pytest
import requests

import nedrex
from nedrex._common import get_pagination_limit
from nedrex.core import (
    get_edges,
    iter_edges,
    iter_nodes,
    get_node_types,
    get_edge_types,
    get_collection_attributes,
    get_node_ids,
    get_nodes,
    api_keys_active,
)
from nedrex.diamond import diamond_submit, check_diamond_status
from nedrex.disorder import (
    get_disorder_ancestors,
    get_disorder_children,
    get_disorder_descendants,
    get_disorder_parents,
    search_by_icd10,
)
from nedrex.domino import (
    domino_submit,
    check_domino_status
)
from nedrex.exceptions import ConfigError, NeDRexError
from nedrex.graph import (
    build_request,
    check_build_status,
    download_graph
)
from nedrex.kpm import kpm_submit, check_kpm_status
from nedrex.must import must_request, check_must_status
from nedrex.neo4j import neo4j_query
from nedrex.ppi import ppis
from nedrex.relations import (
    get_encoded_proteins,
    get_drugs_indicated_for_disorders,
    get_drugs_targeting_proteins,
    get_drugs_targeting_gene_products,
)

from nedrex.static import (get_metadata)

API_URL = "https://dev.api.nedrex.net/licensed/"
API_KEY = requests.post(f"{API_URL}admin/api_key/generate", json={"accept_eula": True}).json()
MODE_OPEN = "open" in API_URL


SEEDS = [
    "P43121",
    "P01589",
    "P30203",
    "P21554",
    "P01579",
    "O43557",
    "Q99572",
    "P01920",
    "P25942",
    "P01189",
    "P21580",
    "Q02556",
    "P01584",
    "P01574",
    "P02649",
    "P29466",
    "P22301",
    "P16581",
    "P06276",
    "P11473",
    "O60333",
    "P19256",
    "Q96P20",
    "P01911",
    "Q2KHT3",
    "P18510",
    "P05362",
    "P01903",
    "P29597",
    "P13232",
    "Q13191",
    "Q06330",
    "P04440",
    "P78508",
    "P19320",
    "P19438",
    "P02774",
    "O75508",
    "P29459",
    "P16871",
    "Q14765",
    "Q16552",
]

UID_REGEX = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@contextmanager
def url_base():
    nedrex.config.set_url_base(API_URL)
    yield
    nedrex.config._url_base = None


@contextmanager
def api_key():
    nedrex.config.set_api_key(API_KEY)
    yield
    nedrex.config._api_key = None


@lru_cache(maxsize=10)
def get_node_collections():
    with api_key(), url_base():
        collections = get_node_types()
    return collections




@lru_cache(maxsize=10)
def get_edge_collections():
    with api_key(), url_base():
        collections = get_edge_types()
    return collections


def get_random_disorder_selection(n, skip_root=True):
    random.seed(20220621)
    with api_key(), url_base():
        disorder_ids = set(get_node_ids("disorder"))
    disorder_ids.remove("mondo.0000001")
    return random.sample(sorted(disorder_ids), n)


def api_to_neo4j_collection_name(collection):
    if collection == "go":
        return "GO"
    indexes = [0]
    curr_idx = 0
    while curr_idx < len(collection):
        try:
            curr_idx = collection.index("_", curr_idx) + 1
            if curr_idx == 0:
                break
            if curr_idx < len(collection) + 1:
                indexes.append(curr_idx)
        except ValueError:
            break
    for idx in indexes:
        if idx == 0:
            collection = collection[idx].upper() + collection[idx + 1:]
        else:
            collection = collection[:idx - 1] + collection[idx].upper() + collection[idx + 1:]
    return collection


def get_embedding_nodes():
    query = """
                    SHOW VECTOR INDEX
                    """
    with api_key(), url_base():
        res = neo4j_query(query)
        entity_names = [(i["labelsOrTypes"][0], i["entityType"]) for i in res]
        return [n for n, k in entity_names if k == "NODE"]


def get_embedding_edges():
    query = """
                    SHOW VECTOR INDEX
                    """
    with api_key(), url_base():
        res = neo4j_query(query)
        entity_names = [(i["labelsOrTypes"][0], i["entityType"]) for i in res]
        return [n for n, k in entity_names if k == "RELATIONSHIP"]


@pytest.fixture
def config():
    return {"api_url": API_URL, "api_key": API_KEY}


@pytest.fixture
def set_api_key(config):
    with api_key():
        yield


@pytest.fixture
def set_base_url(config):
    with url_base():
        yield


def test_set_api_base(set_base_url):
    assert nedrex.config._url_base == API_URL.rstrip("/")


class TestGetNodeTypes:
    @pytest.fixture
    def result(self, set_base_url, set_api_key):
        result = get_node_types()
        return result

    def test_return_type(self, result):
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_ordering(self, result):
        assert result == sorted(result)

    def test_content(self, result):
        assert "protein" in result


class TestGetEdgeTypes:
    @pytest.fixture
    def result(self, set_base_url, set_api_key):
        result = get_edge_types()
        return result

    def test_return_type(self, result):
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_ordering(self, result):
        assert result == sorted(result)

    def test_content(self, result):
        assert "protein_encoded_by_gene" in result


class TestGetCollectionAttributes:
    @pytest.mark.parametrize("collection", get_node_collections())
    def test_get_node_collection_attributes(self, set_base_url, set_api_key, collection):
        expected_attributes = ("primaryDomainId", "domainIds", "type")
        coll_attributes = get_collection_attributes(collection)
        assert all(attr in coll_attributes for attr in expected_attributes)

    @pytest.mark.parametrize("collection", get_edge_collections())
    def test_get_edge_collection_attributes(self, set_base_url, set_api_key, collection):
        # NOTE: Exclude the protein_interacts_with_protein collection because of its size.
        coll_attributes = get_collection_attributes(collection)
        assert "type" in coll_attributes

        assert all(attr in coll_attributes for attr in ("memberOne", "memberTwo")) or all(
            attr in coll_attributes for attr in ("sourceDomainId", "targetDomainId")
        )


class TestGetNodeIds:
    @pytest.mark.parametrize("collection", get_node_collections())
    def test_get_node_ids(self, set_base_url, set_api_key, collection):
        assert get_node_ids(collection)

    @pytest.mark.parametrize("collection", get_edge_collections())
    def test_get_node_ids_fails_for_edges(self, set_base_url, set_api_key, collection):
        with pytest.raises(NeDRexError):
            get_node_ids(collection)


class TestGetEdgeRoutes:
    @pytest.mark.parametrize("collection", get_edge_collections())
    def test_return_type_get_edges(self, set_base_url, set_api_key, collection):
        edges = get_edges(collection, limit=1_000)
        assert isinstance(edges, list)

    @pytest.mark.parametrize("collection", get_edge_collections())
    def test_edge_attributes(self, set_base_url, set_api_key, collection):
        result = get_collection_attributes(collection, include_counts=True)
        total = result["document_count"]
        attr_counts = result["attribute_counts"]

        assert attr_counts["type"] == total
        assert (
            attr_counts.get("memberOne", 0) == attr_counts.get("memberTwo", 0) == total
            and attr_counts.get("sourceDomainId", 0) == attr_counts.get("targetDomainId", 0) == 0
        ) ^ (
            attr_counts.get("memberOne", 0) == attr_counts.get("memberTwo", 0) == 0
            and attr_counts.get("sourceDomainId", 0) == attr_counts.get("targetDomainId", 0) == total
        )


class TestGetNodeRoutes:
    @pytest.mark.parametrize("collection", get_node_collections())
    def test_get_all_nodes(self, set_base_url, set_api_key, collection):
        assert isinstance(get_nodes(collection), list)

    def test_get_specific_nodes(self, set_base_url, set_api_key):
        nodes = get_nodes("disorder", node_ids=["mondo.0000001"])
        assert isinstance(nodes, list)
        assert len(nodes) == 1
        assert nodes[0]["primaryDomainId"] == "mondo.0000001"

    def test_get_drugs_with_api_key(self, set_base_url, set_api_key):
        nodes = get_nodes("drug")
        assert isinstance(nodes, list)

    def test_get_specific_attributes(self, set_base_url, set_api_key):
        nodes = get_nodes("disorder", attributes=["displayName"])
        assert isinstance(nodes, list)
        assert [set(i.keys()) == {"primaryDomainId", "displayName"} for i in nodes]

    def test_get_specific_attribute_and_nodes(self, set_base_url, set_api_key):
        nodes = get_nodes("disorder", attributes=["displayName"], node_ids=["mondo.0000001"])
        assert isinstance(nodes, list)
        assert len(nodes) == 1
        assert nodes[0] == {
            "displayName": "disease",
            "primaryDomainId": "mondo.0000001",
        }

    def test_pagination(self, set_base_url, set_api_key):
        nodes = get_nodes("genomic_variant", limit=1000, offset=1000)
        assert isinstance(nodes, list)
        assert len(nodes) == 1000

    def test_consistent_pagination(self, set_base_url, set_api_key):
        offset = 1234
        limit = 69

        nodes = get_nodes("genomic_variant", limit=limit, offset=offset)

        for _ in range(10):
            nodes_repeat = get_nodes("genomic_variant", limit=limit, offset=offset)
            assert nodes_repeat == nodes


class TestDisorderRoutes:
    def test_search_by_icd10(self, set_base_url, set_api_key):
        # NOTE: There is currently an ICD-10 mapping issue due to MONDO
        search_by_icd10("I52")

    def test_get_disorder_ancestors(self, set_base_url, set_api_key):
        # Check that `disease or disorder`is an ancestor of `lupus nephritis`
        # `disease or disorder` is not a parent of `lupus neprhitis`
        lupus_nephritis = "mondo.0005556"
        disease_or_disorder = "mondo.0000001"

        result = get_disorder_ancestors(lupus_nephritis)
        assert disease_or_disorder in result[lupus_nephritis]

    def test_get_disorder_descendants(self, set_base_url, set_api_key):
        # Check that `lupus nephritis` is a descendant of `inflammatory disease`
        # `lupus nephritis` is not a child of `inflammatory disease`
        inflam_disease = "mondo.0021166"
        lupus_nephritis = "mondo.0005556"

        result = get_disorder_descendants(inflam_disease)
        assert lupus_nephritis in result[inflam_disease]

    def test_get_disorder_parents(self, set_base_url, set_api_key):
        # Check that `glomerulonephritis` is a parent of `lupus nephritis`
        lupus_nephritis = "mondo.0005556"
        glomerulonephritis = "mondo.0002462"

        result = get_disorder_parents("mondo.0005556")
        assert glomerulonephritis in result[lupus_nephritis]

    def test_get_disorder_children(self, set_base_url, set_api_key):
        # Check that `lupus nephritis` is a child of `glomerulonephritis`
        glomerulonephritis = "mondo.0002462"
        lupus_nephritis = "mondo.0005556"

        result = get_disorder_children(glomerulonephritis)
        assert lupus_nephritis in result[glomerulonephritis]

    @pytest.mark.parametrize("chosen_id", get_random_disorder_selection(50))
    def test_parent_child_reciprocity(self, set_base_url, set_api_key, chosen_id):
        parents = get_disorder_parents(chosen_id)
        if not parents:
            assert True
            return
        children_of_parents = get_disorder_children(parents[chosen_id])
        assert all(chosen_id in value for value in children_of_parents.values())

    @pytest.mark.parametrize("chosen_id", get_random_disorder_selection(20))
    def test_ancestor_descendant_reciprocity(self, set_base_url, set_api_key, chosen_id):
        parents = get_disorder_ancestors(chosen_id)
        descendants_of_parents = get_disorder_descendants(parents[chosen_id])
        assert all(chosen_id in value for value in descendants_of_parents.values())


class TestRoutesFailWithoutAPIUrl:
    def test_get_node_type(self, set_api_key):
        with pytest.raises(ConfigError) as excinfo:
            get_node_types()
        assert "API URL is not set in the config" == str(excinfo.value)

    def test_get_edge_type(self, set_api_key):
        with pytest.raises(ConfigError) as excinfo:
            get_edge_types()
        assert "API URL is not set in the config" == str(excinfo.value)


class TestRoutesFailWithoutAPIKey:
    def test_get_node_type(self, set_base_url):
        if not api_keys_active():
            return

        with pytest.raises(ConfigError) as excinfo:
            get_node_types()
        assert "no API key set in the configuration" == str(excinfo.value)

        if not api_keys_active():
            return

        with pytest.raises(ConfigError) as excinfo:
            get_edge_types()
        assert "no API key set in the configuration" == str(excinfo.value)

    @pytest.mark.parametrize("collection", get_node_collections())
    def test_node_routes_fail(self, set_base_url, collection):
        if not api_keys_active():
            return

        with pytest.raises(ConfigError) as excinfo:
            get_collection_attributes(collection)
        assert "no API key set in the configuration" == str(excinfo.value)

        with pytest.raises(ConfigError) as excinfo:
            get_node_ids(collection)
        assert "no API key set in the configuration" == str(excinfo.value)

        with pytest.raises(ConfigError) as excinfo:
            get_nodes(collection)
        assert "no API key set in the configuration" == str(excinfo.value)

        with pytest.raises(ConfigError) as excinfo:
            for _ in take(1, iter_nodes(collection)):
                pass
        assert "no API key set in the configuration" == str(excinfo.value)

    @pytest.mark.parametrize("collection", get_edge_collections())
    def test_edge_routes_fail(self, set_base_url, collection):
        if not api_keys_active():
            return

        with pytest.raises(ConfigError) as excinfo:
            get_collection_attributes(collection)
        assert "no API key set in the configuration" == str(excinfo.value)

        with pytest.raises(ConfigError) as excinfo:
            get_edges(collection)
        assert "no API key set in the configuration" == str(excinfo.value)

        with pytest.raises(ConfigError) as excinfo:
            for _ in take(1, iter_edges(collection)):
                pass
        assert "no API key set in the configuration" == str(excinfo.value)

    # def test_disorder_routes_fail(self, set_base_url):
    #     disorder_id = "mondo.0000001"  # root of the MONDO tree
    #     icd10_id = "I59.1"  # Heart disease, unspecified
    #
    #     with pytest.raises(ConfigError) as excinfo:
    #         get_disorder_children(disorder_id)
    #         if not MODE_OPEN:
    #             assert "no API key set in the configuration" == str(excinfo.value)
    #         else:
    #             assert True
    #
    #     with pytest.raises(ConfigError) as excinfo:
    #         get_disorder_parents(disorder_id)
    #         if not MODE_OPEN:
    #             assert "no API key set in the configuration" == str(excinfo.value)
    #         else:
    #             assert True
    #
    #     with pytest.raises(ConfigError) as excinfo:
    #         get_disorder_ancestors(disorder_id)
    #         if not MODE_OPEN:
    #             assert "no API key set in the configuration" == str(excinfo.value)
    #         else:
    #             assert True
    #
    #     with pytest.raises(ConfigError) as excinfo:
    #         get_disorder_descendants(disorder_id)
    #         if not MODE_OPEN:
    #             assert "no API key set in the configuration" == str(excinfo.value)
    #         else:
    #             assert True
    #
    #     with pytest.raises(ConfigError) as excinfo:
    #         search_by_icd10(icd10_id)
    #         if not MODE_OPEN:
    #             assert "no API key set in the configuration" == str(excinfo.value)
    #         else:
    #             assert True

    def test_disorder_routes_fail(self, set_base_url):
        disorder_id = "mondo.0000001"  # root of the MONDO tree
        icd10_id = "I59.1"  # Heart disease, unspecified

        if not MODE_OPEN:
            # Test cases for when API key is required
            with pytest.raises(ConfigError, match="no API key set in the configuration"):
                get_disorder_children(disorder_id)

            with pytest.raises(ConfigError, match="no API key set in the configuration"):
                get_disorder_parents(disorder_id)

            with pytest.raises(ConfigError, match="no API key set in the configuration"):
                get_disorder_ancestors(disorder_id)

            with pytest.raises(ConfigError, match="no API key set in the configuration"):
                get_disorder_descendants(disorder_id)

            with pytest.raises(ConfigError, match="no API key set in the configuration"):
                search_by_icd10(icd10_id)
        else:
            # Test cases for open mode - these should not raise exceptions
            try:
                get_disorder_children(disorder_id)
                get_disorder_parents(disorder_id)
                get_disorder_ancestors(disorder_id)
                get_disorder_descendants(disorder_id)
                search_by_icd10(icd10_id)
            except ConfigError:
                pytest.fail("Should not raise ConfigError in open mode")


class TestPPIRoute:
    def test_ppi_route(self, set_base_url, set_api_key):
        assert len(ppis(["exp"], 0, get_pagination_limit())) == get_pagination_limit()

    def test_ppi_route_reviewed_filter_true(self, set_base_url, set_api_key):
        ppis(["exp"], 0, get_pagination_limit(), [True], 1000, 800)

    def test_ppi_route_reviewed_filter_false(self, set_base_url, set_api_key):
        ppis(["exp"], 0, get_pagination_limit(), [False], 1000, 800)

    def test_overlap_with_pagination(self, set_base_url, set_api_key):
        page_limit = 1_000
        delta = page_limit // 2
        skip = delta

        previous = ppis(["exp"], 0, page_limit)

        for _ in range(100):
            current = ppis(["exp"], skip, page_limit)
            assert previous[-delta:] == current[:delta]
            previous = current
            skip += delta

    def test_each_evidence_type_works(self, set_base_url, set_api_key):
        for evidence_type in ["exp", "pred", "ortho"]:
            results = ppis([evidence_type], 0, get_pagination_limit())
            assert all(evidence_type in doc["evidenceTypes"] for doc in results)

    def test_fails_with_invalid_type(self, set_base_url, set_api_key):
        for evidence_type in ["exps", "pr3d", "orth"]:
            with pytest.raises(NeDRexError) as excinfo:
                ppis([evidence_type])
            err_val = {evidence_type}
            assert str(excinfo.value) == f"unexpected evidence types: {err_val}"

    def test_fails_with_large_limit(self, set_base_url, set_api_key):
        page_limit = get_pagination_limit()
        with pytest.raises(NeDRexError) as excinfo:
            ppis(["exp"], limit=page_limit + 1)

        assert str(excinfo.value) == f"limit={page_limit + 1:,} is too great (maximum is {page_limit:,})"


class TestRelationshipRoutes:
    def test_get_encoded_proteins(self, set_base_url, set_api_key):
        # NOTE: If result changes, check these examples are still accurate.

        histamine_receptor_genes = ["3269", 3274, "entrez.11255"]  # HRH1, as str  # HRH2, as int  # HRH3, as prefix

        results = get_encoded_proteins(histamine_receptor_genes)

        assert "P35367" in results["3269"]
        assert "P25021" in results["3274"]
        assert "Q9Y5N1" in results["11255"]

    def test_get_drugs_indicated_for_disorders(self, set_base_url, set_api_key):
        # NOTE: If result changes, check these examples are still accurate.

        disorders = [
            "mondo.0005393",  # Gout
            "0005362",  # ED
        ]

        results = get_drugs_indicated_for_disorders(disorders)

        assert "DB00437" in results["0005393"]  # Allopurinol for gout
        assert "DB00203" in results["0005362"]  # Sildenafil for ED

    def test_get_drugs_targeting_proteins(self, set_base_url, set_api_key):
        # NOTE: If result changes, check these examples are still accurate.

        proteins = [
            "P35367",  # Histamine H1 receptor, targetted by antihistamines
            "uniprot.P03372",  # Estrogen receptor α, targetted by ethinylestradiol
        ]

        results = get_drugs_targeting_proteins(proteins)

        assert "DB00341" in results["P35367"]
        assert "DB00977" in results["P03372"]

    def test_get_drugs_targeting_gene_products(self, set_base_url, set_api_key):
        genes = [
            "entrez.3269",  # HRH1 gene (product targetted by antihistamines)
            2099,  # Estrogen receptor α gene (product targetted by ethinylestradiol)
            "6532",  # SLC6A4, encodes Sodium-dependent serotonin transporter, targetted by SSRIs
        ]

        results = get_drugs_targeting_gene_products(genes)

        assert "DB00341" in results["3269"]
        assert "DB00977" in results["2099"]
        assert "DB00215" in results["6532"]


class TestGraphRoutes:
    def test_default_build(self, set_base_url, set_api_key):
        build_request()

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"nodes": ["this_is_not_a_node"]},
            {"edges": ["this_is_not_an_edge"]},
            {"ppi_evidence": ["made_up"]},
            {"taxid": ["human"]},
        ],
    )
    def test_build_fails_with_invalid_params(self, kwargs, set_base_url, set_api_key):
        with pytest.raises(NeDRexError):
            build_request(**kwargs)

    def test_get_uid(self, set_base_url, set_api_key):
        uid = build_request()
        assert UID_REGEX.match(uid)
        check_build_status(uid)

    def test_fails_with_invalid_uid(self, set_base_url, set_api_key):
        uid = "this-is-not-a-valid-uid!"
        with pytest.raises(NeDRexError):
            check_build_status(uid)

    def test_download_fails_with_invalid_uid(self, set_base_url, set_api_key):
        uid = "this-is-not-a-valid-uid!"
        with pytest.raises(NeDRexError):
            download_graph(uid)


class TestKPMRoutes:
    def test_simple_request(self, set_base_url, set_api_key):
        uid = kpm_submit(SEEDS, 10)
        assert UID_REGEX.match(uid)

    def test_kpm_status(self, set_base_url, set_api_key):
        uid = kpm_submit(SEEDS, 10)
        status = check_kpm_status(uid)
        assert isinstance(status, dict)
        assert 'status' in status.keys()


class TestMustRoutes:
    def test_simple_request(self, set_base_url, set_api_key):
        uid = must_request(SEEDS, 0.5, True, 10, 2)
        assert UID_REGEX.match(uid)

    def test_must_status(self, set_base_url, set_api_key):
        uid = must_request(SEEDS, 0.5, True, 10, 2)
        status = check_must_status(uid)
        assert isinstance(status, dict)
        assert "status" in status.keys()

    @pytest.mark.parametrize(
        "update",
        [
            {"hubpenalty": 1.01},
            {"hubpenalty": -0.01},
            {"hubpenalty": None},
            {"multiple": None},
            {"trees": -1},
            {"trees": None},
            {"maxit": -1},
            {"maxit": None},
        ],
    )
    def test_must_fails_with_invalid_arguments(self, set_base_url, set_api_key, update):
        kwargs = {"seeds": SEEDS, "hubpenalty": 0.5, "multiple": True, "trees": 10, "maxit": 2, "network": "DEFAULT"}

        with pytest.raises(NeDRexError):
            kwargs = {**kwargs, **update}
            must_request(**kwargs)


class TestDiamondRoutes:
    def test_simple_request(self, set_base_url, set_api_key):
        uid = diamond_submit(SEEDS, 10)
        assert UID_REGEX.match(uid)

    def test_diamond_status(self, set_base_url, set_api_key):
        uid = diamond_submit(SEEDS, 10)
        status = check_diamond_status(uid)
        assert isinstance(status, dict)
        assert "status" in status.keys()

    def test_diamond_fails_with_invalid_arguments(self, set_base_url, set_api_key):
        with pytest.raises(ValueError):
            diamond_submit(SEEDS, n=10, edges="some")


class TestDominoRoutes:
    def test_simple_request(self, set_base_url, set_api_key):
        uid = domino_submit(SEEDS)
        assert UID_REGEX.match(uid)

    def test_check_domino_status(self, set_base_url, set_api_key):
        uid = domino_submit(SEEDS)
        status = check_domino_status(uid)
        assert isinstance(status, dict)
        assert "status" in status.keys()


class TestNeo4j:
    def test_general_node_query(self, set_base_url, set_api_key):
        query = """
        MATCH (n: Gene)
        RETURN n
        LIMIT 25
        """

        assert all(i["n"]["type"] == "Gene" for i in neo4j_query(query))

    def test_general_edge_query(self, set_base_url, set_api_key):
        query = """
        MATCH ()-[n:GeneAssociatedWithDisorder]-()
        RETURN n
        LIMIT 25
        """

        assert all(i["n"]["type"] == "GeneAssociatedWithDisorder" for i in neo4j_query(query))

    def test_general_node_query_with_attributes(self, set_base_url, set_api_key):
        query = """
        MATCH (n: Gene {approvedSymbol: 'A1BG'})
        RETURN n
        """

        x = list(neo4j_query(query))
        assert len(x) == 1
        assert x[0]["n"]['chromosome'] == '19'


    def test_general_edge_query_with_attributes(self, set_base_url, set_api_key):
        query = """
        MATCH ()-[n: GeneAssociatedWithDisorder {score: 1.0}]-()
        RETURN n
        LIMIT 1000
        """

        results = list(neo4j_query(query))
        assert len(results) != 0
        assert all(i["n"]['score'] == 1.0 for i in results)


    def test_gene_associated_with_disorder(self, set_base_url, set_api_key):
        query = """
        MATCH (g: Gene)-[gawd: GeneAssociatedWithDisorder]-(d: Disorder)
        RETURN g, d, gawd
        LIMIT 50
        """

        for row in neo4j_query(query):
            gene, disorder, assoc = row["g"], row["d"], row["gawd"]
            assert gene['type'] == 'Gene'
            assert disorder['type'] == "Disorder"
            assert assoc['type'] == "GeneAssociatedWithDisorder"

    def test_write_fails(self, set_base_url, set_api_key):
        query = """
        CREATE (n: SomeRandomNode)
        """

        with pytest.raises(NeDRexError):
            for _ in neo4j_query(query):
                pass

    @pytest.mark.parametrize("collection", get_node_collections())
    def test_node_unique_constraints(self, set_base_url, set_api_key, collection):
        skip = {"genomic_variant"}
        if collection in skip:
            assert True
            return
        neo4j_collection = api_to_neo4j_collection_name(collection)
        query = f"SHOW CONSTRAINTS WHERE '{neo4j_collection}' IN labelsOrTypes AND 'primaryDomainId' IN properties AND type IN ['NODE_KEY', 'UNIQUENESS', 'NODE_PROPERTY_UNIQUENESS'];"
        res = neo4j_query(query)
        assert res is not None and len([i for i in res]) == 1



class TestStaticRoutes:
   # @lru_cache(maxsize=10)
    def test_metadata(self, set_base_url, set_api_key):
        metadata = get_metadata()
        assert type(metadata) == dict
        assert "version" in metadata.keys()

    def test_source_db_contains_metadata(self, set_base_url, set_api_key):
        metadata = get_metadata()
        assert type(metadata) == dict
        assert len(metadata["source_databases"].keys()) > 0
        for db in metadata["source_databases"].keys():
            assert metadata["source_databases"][db]["version"] is not None

class TestEmbeddings:


    def test_created_indexes(self, set_base_url, set_api_key):
        query = """
        SHOW VECTOR INDEX
        """
        res = list(neo4j_query(query))
        assert res
        assert all(i["populationPercent"] == 100.0 and i["state"] == "ONLINE" for i in res)




    @pytest.mark.parametrize("node", get_embedding_nodes())
    def test_node_embeddings_not_empty(self, set_base_url, set_api_key, node):

        query = f"MATCH (n:{node}) RETURN n.embedding LIMIT 25"
        assert all(i["n.embedding"] is not None and not all(j == 0.0  for j in i["n.embedding"]) for i in neo4j_query(query)), f"Broken embedding for {node}"


    @pytest.mark.parametrize("edge", get_embedding_edges())
    def test_edge_embeddings_not_empty(self, set_base_url, set_api_key, edge):

        query = f"MATCH ()-[n:{edge}]-() RETURN n.embedding LIMIT 25"
        assert all(i["n.embedding"] is not None and not all(j == 0.0 for j in i["n.embedding"]) for i in neo4j_query(query)), f"Broken embedding for {edge}"

