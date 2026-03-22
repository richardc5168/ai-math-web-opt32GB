"""Tests for concept taxonomy."""

from learning.concept_taxonomy import (
    CONCEPT_TAXONOMY,
    get_concept,
    get_display_name,
    get_prerequisites,
    get_all_prerequisites,
    resolve_concept_ids,
    list_domains,
    concepts_by_domain,
    all_concept_ids,
    TOPIC_TAG_TO_CONCEPT,
)


def test_taxonomy_not_empty():
    assert len(CONCEPT_TAXONOMY) >= 30


def test_every_concept_has_required_fields():
    required = {"display_name_zh", "domain", "grade", "prerequisites", "difficulty_base"}
    for cid, c in CONCEPT_TAXONOMY.items():
        missing = required - set(c.keys())
        assert not missing, f"{cid} missing fields: {missing}"


def test_prerequisites_reference_valid_concepts():
    all_ids = set(CONCEPT_TAXONOMY.keys())
    for cid, c in CONCEPT_TAXONOMY.items():
        for prereq in c["prerequisites"]:
            assert prereq in all_ids, f"{cid} has unknown prerequisite: {prereq}"


def test_no_circular_prerequisites():
    """Ensure no concept is a prerequisite of itself (directly or transitively)."""
    for cid in CONCEPT_TAXONOMY:
        all_prereqs = get_all_prerequisites(cid)
        assert cid not in all_prereqs, f"{cid} has circular prerequisite chain"


def test_get_concept_returns_record():
    c = get_concept("frac_multiply")
    assert c is not None
    assert c["display_name_zh"] == "分數乘法"
    assert c["domain"] == "fraction"


def test_get_concept_returns_none_for_unknown():
    assert get_concept("nonexistent_xyz") is None


def test_get_display_name():
    assert get_display_name("percent_concept") == "百分率基本概念"
    assert get_display_name("unknown_id") == "unknown_id"


def test_get_prerequisites():
    prereqs = get_prerequisites("frac_add_unlike")
    assert "frac_add_like" in prereqs
    assert "lcm_basic" in prereqs


def test_get_all_prerequisites_transitive():
    all_prereqs = get_all_prerequisites("frac_word_problem")
    assert "frac_multiply" in all_prereqs
    assert "frac_simplify" in all_prereqs
    assert "frac_concept_basic" in all_prereqs


def test_resolve_concept_ids_from_topic_tags():
    ids = resolve_concept_ids(["ratio_percent", "discount"])
    assert "percent_concept" in ids
    assert "discount_calc" in ids


def test_resolve_concept_ids_from_concept_points():
    ids = resolve_concept_ids([], ["求某數的百分之幾：用乘法"])
    assert "percent_of_number" in ids


def test_list_domains():
    domains = list_domains()
    assert "fraction" in domains
    assert "decimal" in domains
    assert "percent" in domains


def test_concepts_by_domain():
    frac = concepts_by_domain("fraction")
    assert "frac_multiply" in frac
    assert "decimal_basic" not in frac


def test_all_concept_ids_sorted():
    ids = all_concept_ids()
    assert ids == sorted(ids)
    assert len(ids) == len(CONCEPT_TAXONOMY)


def test_topic_tag_mapping_references_valid_concepts():
    all_ids = set(CONCEPT_TAXONOMY.keys())
    for tag, cids in TOPIC_TAG_TO_CONCEPT.items():
        for cid in cids:
            assert cid in all_ids, f"topic_tag '{tag}' maps to unknown concept: {cid}"
