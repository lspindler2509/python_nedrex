"""Regression checks for existing calls supported on v2d_update."""

import importlib
import json

import pytest
import requests

from nedrex import _common, comorbiditome, config, core, graph, neo4j, ppi, validation, variants


@pytest.fixture
def wire(monkeypatch):
    monkeypatch.setattr(config, "_url_base", "https://legacy.example/open")
    monkeypatch.setattr(config, "_api_key", "key")
    monkeypatch.setattr(core, "_check_type", lambda *args: True)
    monkeypatch.setattr(core, "_get_pagination_limit", lambda: 10)
    monkeypatch.setattr(ppi, "_get_pagination_limit", lambda: 10)
    calls = []

    def send(method, url, **kwargs):
        calls.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = b"[]"
        return response

    monkeypatch.setattr(_common.http, "request", send)
    return calls


def test_existing_node_and_edge_pagination_inputs(wire, monkeypatch):
    assert core.get_nodes("protein", limit=0, offset=None) == []
    assert wire[-1][2]["params"] == {"node_id": None, "attribute": None, "offset": None, "limit": 0}
    # Existing edge calls must not acquire a dependency on /pagination_max.
    monkeypatch.setattr(core, "_get_pagination_limit", lambda: pytest.fail("extra pagination request"))
    assert core.get_edges("drug_has_target", limit=20) == []
    assert wire[-1][2]["params"] == {"limit": 20, "offset": None, "api_key": "key"}


def test_existing_ppi_defaults_and_explicit_none(wire):
    ppi.ppis(["exp"])
    assert wire[-1][2]["json"] == {
        "iid_evidence": ["exp"],
        "skip": 0,
        "limit": None,
        "reviewed_proteins": [True, False],
        "skip_proteins": 0,
        "limit_proteins": 250000,
    }
    ppi.ppis(["exp"], 0, 0, None, None, None)
    body = wire[-1][2]["json"]
    assert body["limit"] == 0
    assert all(body[key] is None for key in ["reviewed_proteins", "skip_proteins", "limit_proteins"])


def test_graph_does_not_send_new_fields_unless_requested(wire):
    graph.build_request()
    assert "reviewed_proteins" not in wire[-1][2]["json"]
    graph.build_request(reviewed_proteins=[True])
    assert wire[-1][2]["json"]["reviewed_proteins"] == [True]


@pytest.mark.parametrize("drugs", [["DB00001"], [("DB00001", 0.5)]])
def test_drug_validation_preserves_legacy_and_current_payloads(wire, drugs):
    validation.drug_validation_submit(drugs, ["DB00001"], 100)
    assert wire[-1][2]["json"]["test_drugs"] == drugs
    assert json.loads(json.dumps(wire[-1][2]["json"]))["test_drugs"][0] != list("DB00001")


@pytest.mark.parametrize(
    "function,argument",
    [
        (comorbiditome.map_icd10_to_mondo, ["E11"]),
        (comorbiditome.map_mondo_to_icd10, ["mondo.0005148"]),
    ],
)
def test_existing_mapping_calls_use_current_post_contract(wire, function, argument):
    assert function(argument) == []
    assert len(wire) == 1
    assert wire[0][0].lower() == "post"
    assert argument in wire[0][2]["json"].values()


@pytest.mark.parametrize(
    "iterator,fetch_name",
    [
        (variants.iter_variant_gene_associations, "get_variant_gene_associations"),
        (variants.iter_variant_disorder_associations, "get_variant_disorder_associations"),
    ],
)
def test_variants_continue_after_short_or_identical_pages(monkeypatch, iterator, fetch_name):
    monkeypatch.setattr(variants, "_get_pagination_limit", lambda: 3)
    calls = []

    def fetch(*args, **kwargs):
        calls.append(kwargs["offset"])
        return [{"id": "same"}] if kwargs["offset"] < 6 else []

    monkeypatch.setattr(variants, fetch_name, fetch)
    assert list(iterator()) == [{"id": "same"}, {"id": "same"}]
    assert calls == [0, 3, 6]


@pytest.mark.parametrize(
    "module,function,args,fields",
    [
        ("closeness", "closeness_submit", (["P00533"],), ["N"]),
        ("trustrank", "trustrank_submit", (["P00533"],), ["N"]),
        (
            "comorbiditome",
            "submit_comorbiditome_build",
            (),
            ["mondo", "max_phi_cor", "min_phi_cor", "max_p_value", "min_p_value"],
        ),
    ],
)
def test_existing_optional_none_values_are_not_rewritten(wire, module, function, args, fields):
    getattr(importlib.import_module("nedrex." + module), function)(*args)
    body = wire[-1][2]["json"]
    assert all(field in body and body[field] is None for field in fields)


def test_neo4j_stream_preserves_named_rows_and_column_order(wire, monkeypatch):
    rows = [{"first": 1, "second": 2}, {"first": 3, "second": 4}]

    def send(method, url, **kwargs):
        wire.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = b"\n".join(json.dumps([row]).encode() for row in rows)
        response._content_consumed = True
        return response

    monkeypatch.setattr(_common.http, "request", send)
    result = list(neo4j.neo4j_query("RETURN 1 AS first, 2 AS second"))
    assert result == rows
    assert list(result[0]) == ["first", "second"]
    assert wire[0][0].lower() == "post"
    assert wire[0][2]["json"]["stream"] is True
