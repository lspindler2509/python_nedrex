=======
History
=======

0.2.0 (unreleased)
------------------

* Renamed ``relations.get_drugs_targetting_proteins`` to
  ``get_drugs_targeting_proteins`` and ``get_drugs_targetting_gene_products`` to
  ``get_drugs_targeting_gene_products``. The old names remain as deprecated
  aliases that emit a ``DeprecationWarning``.
* Relation calls use POST with ``{"nodes": [...]}`` bodies, matching the current
  API; the previous GET requests to the misspelled routes returned HTTP 404.
* Errors for HTTP 404 now report the request method and URL.
* Added ``request`` and ``iter_pages`` helpers and ``core`` lookup, mapping and
  attribute functions for the public API routes.
* Added ``embeddings`` (``get_available``, ``query``). ``query`` rejects unknown
  collection names (case-sensitive) before sending the request.
* Added ``translate`` (``translate_entrez``, ``translate_uniprot``).
* Added ``comorbiditome`` ICD-10/MONDO mapping routes and ``disorder`` hierarchy
  and ICD-10 search functions.
* ``ppi.ppis`` uses POST and accepts the API's filters (``reviewed_proteins``,
  protein window, ``nodes``, ``sources``, ``num_sources`` and methods-score
  cutoffs). Added ``ppi.iter_ppis``, which pages through all matching PPIs.
* Added ``ppi.ppi_network``, which downloads all matching PPIs as a deduplicated,
  undirected edge list of UniProt accessions, optionally in a compact
  ``{"nodes", "edges"}`` format with positions.
* Added ``static.get_icd10_mondo_map`` and ``static.get_icd10_omim_map``, which
  return the server's tab-separated text.

0.1.4
-----

* Previous release on PyPI.

0.1.0 (2022-02-23)
------------------

* First release on PyPI.
