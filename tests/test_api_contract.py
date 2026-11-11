"""Offline request routes and pagination; no live services or EULA acceptance."""

import importlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests

from nedrex import (
    _common,
    bicon,
    comorbiditome,
    config,
    core,
    embeddings,
    graph,
    neo4j,
    ppi,
    relations,
    static,
    translate,
    validation,
    variants,
)
from nedrex.exceptions import ConfigError, NeDRexError

EXPECTED_ROUTES = {
    ("get", "/open/pagination_max"),
    ("get", "/open/api_key_setting"),
    ("get", "/open/list_node_collections"),
    ("get", "/open/list_edge_collections"),
    ("get", "/open/{collection_name}/attributes"),
    ("get", "/open/{collection_name}/attributes/{attribute}/{format}"),
    ("post", "/open/{collection_name}/attributes/{format}"),
    ("get", "/open/{collection_name}/attributes/{format}"),
    ("get", "/open/{collection}/details"),
    ("get", "/open/{collection}/all"),
    ("get", "/open/get_by_id/{collection}/{q}"),
    ("post", "/open/find_by_ids/"),
    ("get", "/open/id_map/{collection}"),
    ("get", "/open/entrez_to_uniprot_id"),
    ("post", "/open/entrez_to_uniprot_ids"),
    ("get", "/open/disorder/get_by_icd10"),
    ("get", "/open/disorder/descendants"),
    ("get", "/open/disorder/ancestors"),
    ("get", "/open/disorder/parents"),
    ("get", "/open/disorder/children/"),
    ("post", "/open/ppi"),
    ("post", "/open/relations/get_encoded_proteins"),
    ("post", "/open/relations/get_drugs_indicated_for_disorders"),
    ("post", "/open/relations/get_drugs_targeting_proteins"),
    ("post", "/open/relations/get_drugs_targeting_gene_products"),
    ("post", "/open/graph/builder"),
    ("get", "/open/graph/details/{uid}"),
    ("get", "/open/graph/download/{uid}/{fname}.graphml"),
    ("post", "/open/bicon/submit"),
    ("get", "/open/bicon/status"),
    ("get", "/open/bicon/clustermap"),
    ("get", "/open/bicon/download"),
    ("get", "/open/static/metadata"),
    ("get", "/open/static/licence"),
    ("get", "/open/static/lengths.map"),
    ("get", "/open/static/icd10_omim_map"),
    ("get", "/open/static/icd10_mondo_map"),
    ("post", "/open/must/submit"),
    ("get", "/open/must/status"),
    ("post", "/open/diamond/submit"),
    ("get", "/open/diamond/status"),
    ("get", "/open/diamond/download"),
    ("post", "/open/domino/submit"),
    ("get", "/open/domino/status"),
    ("post", "/open/robust/submit"),
    ("get", "/open/robust/status"),
    ("get", "/open/robust/results"),
    ("post", "/open/kpm/submit"),
    ("get", "/open/kpm/status"),
    ("post", "/open/trustrank/submit"),
    ("get", "/open/trustrank/status"),
    ("get", "/open/trustrank/download"),
    ("post", "/open/closeness/submit"),
    ("get", "/open/closeness/status"),
    ("get", "/open/closeness/download"),
    ("get", "/open/validation/status"),
    ("post", "/open/validation/joint"),
    ("post", "/open/validation/module"),
    ("post", "/open/validation/drug"),
    ("get", "/open/variants/get_effect_choices"),
    ("get", "/open/variants/get_review_choices"),
    ("get", "/open/variants/get_variant_disorder_associations"),
    ("get", "/open/variants/get_variant_gene_associations"),
    ("get", "/open/variants/variant_based_disorder_associated_genes"),
    ("get", "/open/variants/variant_based_gene_associated_disorders"),
    ("post", "/open/neo4j/query"),
    ("get", "/open/neo4j/details/{uid}"),
    ("get", "/open/neo4j/download/{uid}.json"),
    ("post", "/open/comorbiditome/icd10_to_mondo"),
    ("post", "/open/comorbiditome/mondo_to_icd10"),
    ("get", "/open/comorbiditome/get_icd10_associations"),
    ("post", "/open/comorbiditome/submit_comorbiditome_build"),
    ("get", "/open/comorbiditome/comorbiditome_build_status"),
    ("get", "/open/comorbiditome/download_comorbiditome_build/{uid}/{format}/{fname}"),
    ("get", "/open/embeddings/available"),
    ("post", "/open/embeddings/query"),
    ("post", "/open/translate/translate_entrez"),
    ("post", "/open/translate/translate_uniprot"),
}


@pytest.fixture
def capture(monkeypatch):
    old = config.url_base, config.api_key
    config.set_url_base("https://example.org/open")
    config.set_api_key("test-key")
    _common._pagination_limit_cache.clear()
    seen = set()
    calls = []

    def send(method, url, **kwargs):
        path = urlsplit(url).path
        matches = [
            template
            for expected_method, template in EXPECTED_ROUTES
            if method.lower() == expected_method and re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", template), path)
        ]
        assert matches, (method, path)
        seen.add((method.lower(), matches[0]))
        calls.append((method.lower(), path, kwargs))
        data = []
        if path.endswith("pagination_max"):
            data = 2
        elif path.endswith("list_node_collections"):
            data = ["protein", "gene", "drug", "disorder", "variant"]
        elif path.endswith("list_edge_collections"):
            data = ["drug_has_target"]
        elif path.endswith("api_key_setting"):
            data = False
        elif path.endswith("embeddings/available"):
            data = ["Protein"]
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(data).encode()
        response._content_consumed = True
        response.url = url
        return response

    monkeypatch.setattr(_common.http, "request", send)
    monkeypatch.setattr(_common.requests, "get", lambda url, **kwargs: send("get", url, **kwargs))
    monkeypatch.setattr(_common.urllib.request, "install_opener", lambda opener: None)

    def retrieve(url, target):
        response = send("get", url)
        Path(target).write_bytes(response.content)
        return target, None

    monkeypatch.setattr(_common.urllib.request, "urlretrieve", retrieve)
    yield seen, calls
    config._url_base, config._api_key = old
    _common._pagination_limit_cache.clear()


def test_supported_public_operations_have_request_contracts(capture, tmp_path):
    """Exercise supported routes; Chat and the redundant short graph-download route are excluded."""
    core.api_keys_active()
    core.get_pagination_limit()
    core.get_node_types()
    core.get_edge_types()
    core.get_collection_attributes("protein", True)
    core.get_node_ids("protein")
    core.get_nodes("protein", limit=1)
    core.get_edges("drug_has_target", limit=1)
    core.get_collection_details("protein")
    core.get_attribute_values("protein", "primaryDomainId")
    core.get_edges(
        "drug_has_target",
        attributes=["sourceDomainId"],
        source_domain_ids=["drugbank.DB00001"],
        target_domain_ids=["uniprot.P00533"],
        limit=1,
    )
    core.get_by_id("protein", "uniprot.P00533")
    core.find_by_ids("protein", ["uniprot.P00533"])
    core.map_ids("protein", ["P00533"])
    core.entrez_to_uniprot_id("1956")
    core.entrez_to_uniprot_ids(["1956"])
    disorder = importlib.import_module("nedrex.disorder")
    for function in [
        "search_by_icd10",
        "get_disorder_descendants",
        "get_disorder_ancestors",
        "get_disorder_parents",
        "get_disorder_children",
    ]:
        getattr(disorder, function)(["mondo.0005148"])
    ppi.ppis(
        ["exp"], limit=1, nodes=["uniprot.P00533"], sources=["IntAct"], num_sources=1, hippie_methods_score_cutoff=0.1
    )
    relations.get_encoded_proteins([1956])
    relations.get_drugs_indicated_for_disorders(["0005148"])
    relations.get_drugs_targeting_proteins(["P00533"])
    relations.get_drugs_targeting_gene_products([1956])
    graph.build_request(reviewed_proteins=[True])
    graph.check_build_status("job")
    graph.download_graph("job", str(tmp_path / "named.graphml"), filename="named")
    bicon.bicon_request(io.StringIO("gene\tsample\n1956\t1\n"))
    bicon.check_bicon_status("job")
    bicon.download_bicon_data("job", str(tmp_path / "bicon.zip"))
    bicon.download_bicon_clustermap("job", str(tmp_path / "bicon.png"))
    static.get_metadata()
    static.get_license()
    static.download_lengths_map(str(tmp_path / "lengths.map"))
    static.get_icd10_omim_map()
    static.get_icd10_mondo_map()
    for module, function, args in [
        ("must", "must_request", (["1956"], 0.1, False, 1, 10)),
        ("diamond", "diamond_submit", (["1956"], 1)),
        ("domino", "domino_submit", (["1956"],)),
        ("robust", "robust_submit", (["1956"],)),
        ("kpm", "kpm_submit", (["1956"], 1)),
        ("trustrank", "trustrank_submit", (["P00533"], 0.85, True, True, 10)),
        ("closeness", "closeness_submit", (["P00533"], True, True, 10)),
    ]:
        module = importlib.import_module("nedrex." + module)
        getattr(module, function)(*args)
        prefix = module.__name__.split(".")[-1]
        getattr(module, "check_{}_status".format(prefix))("job")
        download = getattr(module, "download_{}_results".format(prefix), None)
        if download:
            download("job")
    validation.check_validation_status("job")
    validation.joint_validation_submit(["1956"], "gene", ["DB00001"], ["DB00001"], 1)
    validation.module_validation_submit(["1956"], "gene", ["DB00001"], 1)
    validation.drug_validation_submit([("DB00001", 0.5)], ["DB00001"], 1000)
    variants.get_effect_choices()
    variants.get_review_status_choices()
    variants.get_variant_disorder_associations(limit=1)
    variants.get_variant_gene_associations(limit=1)
    variants.get_variant_based_disorder_associated_genes("mondo.0005148")
    variants.get_variant_based_gene_associated_disorders("entrez.1956")
    list(neo4j.neo4j_query("RETURN 1"))
    neo4j.query("RETURN 1", download=True)
    neo4j.check_query_status("job")
    neo4j.download_query_results("job", str(tmp_path / "query.json"))
    comorbiditome.map_icd10_to_mondo(["E11"])
    comorbiditome.map_mondo_to_icd10(["mondo.0005148"])
    comorbiditome.get_icd10_associations(["entrez.1956"], "gene_associated_with_disorder")
    comorbiditome.submit_comorbiditome_build(1.0, 0.0, 1.0, 0.0, [])
    comorbiditome.check_comorbiditome_status("job")
    comorbiditome.download_comorbiditome_build("job", "tsv")
    embeddings.get_available()
    embeddings.query("EGFR", "Protein", 1)
    translate.translate_entrez(["EGFR"])
    translate.translate_uniprot(["EGFR"])
    assert capture[0] == EXPECTED_ROUTES


def test_pagination_limits_filters_and_partial_final_page(monkeypatch):
    monkeypatch.setattr(_common, "get_pagination_limit", lambda: 3)
    calls = []

    def fetch(**page):
        calls.append(page)
        return [{"id": i} for i in range(page["offset"], min(10, page["offset"] + page["limit"]))]

    assert list(_common.iter_pages(fetch, page_size=3, offset=2, max_records=5)) == [{"id": i} for i in range(2, 7)]
    assert calls == [{"offset": 2, "limit": 3}, {"offset": 5, "limit": 2}]
    assert len(list(_common.iter_pages(fetch, page_size=3, offset=8))) == 2
    assert list(_common.iter_pages(fetch, max_records=0)) == []
    assert list(_common.iter_pages(lambda **kw: [{"id": 1}], page_size=1, max_records=2)) == [{"id": 1}, {"id": 1}]


@pytest.mark.parametrize(
    "iterator,filters",
    [
        (core.iter_nodes, {"node_type": "protein", "node_ids": ["uniprot.P00533"]}),
        (core.iter_edges, {"edge_type": "drug_has_target"}),
        (
            core.iter_edges,
            {
                "edge_type": "drug_has_target",
                "source_domain_ids": ["drugbank.DB00001"],
                "target_domain_ids": ["uniprot.P00533"],
            },
        ),
        (ppi.iter_ppis, {"nodes": ["uniprot.P00533"], "sources": ["IntAct"]}),
    ],
)
def test_iterators_preserve_filters(capture, monkeypatch, iterator, filters):
    def pages(fetch, page_size, offset, max_records, **kwargs):
        fetch(offset=4, limit=1)
        fetch(offset=5, limit=1)
        return iter([])

    module = importlib.import_module(iterator.__module__)
    monkeypatch.setattr(module, "_iter_pages", pages)
    list(iterator(page_size=1, max_records=2, **filters))
    calls = [
        call
        for call in capture[1]
        if "/attributes/" in call[1] or call[1].endswith("/all") or call[1].endswith("/ppi")
    ][-2:]
    for _, _, kwargs in calls:
        payload = kwargs.get("json", kwargs.get("params", {}))
        for key, value in filters.items():
            wire = {
                "node_ids": "node_ids",
                "source_domain_ids": "source_domain_id",
                "target_domain_ids": "target_domain_id",
                "gene_ids": "gene_id",
                "disorder_ids": "disorder_id",
            }.get(key, key)
            if key not in ["node_type", "edge_type", "collection", "use_post"]:
                assert payload[wire] == value
    a = calls[0][2].get("json", calls[0][2].get("params", {}))
    b = calls[1][2].get("json", calls[1][2].get("params", {}))
    key = "skip" if "skip" in a else "offset"
    assert a[key] == 4 and b[key] == 5


def test_embeddings_query_rejects_unknown_collection(capture):
    # collection names are case-sensitive; the query itself must not be sent
    with pytest.raises(NeDRexError, match="Protein"):
        embeddings.query("EGFR", "protein", 1)
    assert [path for _, path, _ in capture[1]] == ["/open/embeddings/available"]


@pytest.mark.parametrize("status", [401, 404, 422])
def test_existing_response_error_handling(status):
    response = requests.Response()
    response.status_code = status
    detail = "An API key is required to access the requested data" if status == 401 else "rejected"
    response._content = json.dumps({"detail": detail}).encode()
    with pytest.raises((NeDRexError, ConfigError)):
        _common.check_response(response)


@pytest.mark.parametrize("size,offset,maximum", [(0, 0, None), (-1, 0, None), (3, -1, None), (1, 0, -1)])
def test_invalid_pagination_does_not_fetch(monkeypatch, size, offset, maximum):
    monkeypatch.setattr(_common, "get_pagination_limit", lambda: 3)

    def fetch(**kwargs):
        pytest.fail("invalid pagination must not fetch a page")

    with pytest.raises(NeDRexError):
        list(_common.iter_pages(fetch, size, offset, maximum))


@pytest.mark.parametrize("base_url", ["https://api.nedrex.net/open", "https://api.nedrex.net/licensed"])
def test_new_routes_keep_configured_base_url_and_key(monkeypatch, base_url):
    monkeypatch.setattr(config, "_url_base", base_url)
    monkeypatch.setattr(config, "_api_key", "configured-key")
    calls = []

    def send(method, url, **kwargs):
        calls.append((url, kwargs["headers"]))
        response = requests.Response()
        response.status_code = 200
        response._content = b"[]"
        return response

    monkeypatch.setattr(_common.http, "request", send)
    assert embeddings.get_available() == []
    assert calls == [(base_url + "/embeddings/available", {"x-api-key": "configured-key"})]


@pytest.mark.parametrize(
    "kind,filtered,fmt",
    [(kind, filtered, fmt) for kind in ["nodes", "edges"] for filtered in [False, True] for fmt in ["json", "tsv"]],
)
def test_queries_select_method_from_id_filters(capture, kind, filtered, fmt):
    if kind == "nodes":
        result = core.get_nodes("protein", ["primaryDomainId"], ["uniprot.P00533"] if filtered else None, 1, 3, fmt)
    else:
        result = core.get_edges(
            "drug_has_target",
            1,
            3,
            ["sourceDomainId"],
            ["drugbank.DB00001"] if filtered else None,
            ["uniprot.P00533"] if filtered else None,
            fmt,
        )
    assert result == ("[]" if fmt == "tsv" else [])
    method, path, kwargs = capture[1][-1]
    assert method == ("post" if filtered else "get")
    assert path.endswith("/attributes/" + fmt)
    payload = kwargs["json" if filtered else "params"]
    assert payload["skip" if filtered else "offset"] == 3
    assert payload["limit"] == 1
    if filtered and kind == "edges":
        assert payload["source_domain_id"] == ["drugbank.DB00001"]
        assert payload["target_domain_id"] == ["uniprot.P00533"]
    elif filtered:
        assert payload["node_ids"] == ["uniprot.P00533"]


def test_ppi_network_deduplicates_and_supports_compact(monkeypatch):
    records = [
        {"memberOne": "uniprot.P2", "memberTwo": "uniprot.P1"},
        {"memberOne": "uniprot.P1", "memberTwo": "uniprot.P2"},
        {"memberOne": "uniprot.P3", "memberTwo": "uniprot.P3"},
        {"memberOne": "uniprot.P1", "memberTwo": "uniprot.P3"},
    ]
    seen = {}

    def fake_iter(evidence, reviewed_proteins, **kwargs):
        seen.update(kwargs, evidence=evidence)
        return iter(records)

    monkeypatch.setattr(ppi, "iter_ppis", fake_iter)
    assert ppi.ppi_network(
        sources=["intact"], max_records=4, skip=2, nodes=["uniprot.P1"], skip_proteins=1, limit_proteins=9
    ) == [
        {"from": "P1", "to": "P2"},
        {"from": "P1", "to": "P3"},
    ]
    assert {k: seen[k] for k in ("sources", "max_records", "skip", "nodes", "skip_proteins", "limit_proteins")} == {
        "sources": ["intact"],
        "max_records": 4,
        "skip": 2,
        "nodes": ["uniprot.P1"],
        "skip_proteins": 1,
        "limit_proteins": 9,
    }
    assert ppi.ppi_network(compact=True) == {"nodes": ["P1", "P2", "P3"], "edges": [[0, 1], [0, 2]]}
