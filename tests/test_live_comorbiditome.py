"""Live comorbiditome requests against the public open API (no mocks, no API key).

Run with NEDREX_LIVE_TESTS=1; skipped otherwise because it needs network access.
"""

import os

import pytest

from nedrex import comorbiditome, config

OPEN_API_URL = "https://api.nedrex.net/open"

pytestmark = pytest.mark.skipif(
    os.environ.get("NEDREX_LIVE_TESTS") != "1", reason="set NEDREX_LIVE_TESTS=1 to run live API tests"
)


@pytest.fixture(autouse=True)
def open_api():
    old = config.url_base, config.api_key
    config.set_url_base(OPEN_API_URL)
    config._api_key = None
    yield
    config._url_base, config._api_key = old


def test_map_icd10_to_mondo():
    result = comorbiditome.map_icd10_to_mondo(["C34.1"])
    assert "mondo.0013631" in result["C34.1"]


def test_map_mondo_to_icd10():
    result = comorbiditome.map_mondo_to_icd10(["mondo.0013631"])
    assert "C34.1" in result["mondo.0013631"]


def test_map_mondo_to_icd10_only_3char():
    result = comorbiditome.map_mondo_to_icd10(["mondo.0013631"], only_3char=True)
    assert result["mondo.0013631"] == ["C34"]


@pytest.mark.parametrize(
    "nodes,edge_type",
    [
        (["entrez.1956"], "gene_associated_with_disorder"),
        (["mondo.0005233"], "drug_has_indication"),
    ],
)
def test_get_icd10_associations(nodes, edge_type):
    result = comorbiditome.get_icd10_associations(nodes, edge_type)
    assert isinstance(result, dict)
    assert set(result) == set(nodes)
